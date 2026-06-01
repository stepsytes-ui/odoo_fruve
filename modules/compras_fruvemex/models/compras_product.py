import re

from odoo import _, api, fields, models
from odoo.osv import expression


class ComprasProduct(models.Model):
    _name = 'compras.product'
    _description = 'Producto de Almacén'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _sql_constraints = [
        ('compras_product_code_unique', 'unique(code)', 'El código del producto debe ser único.'),
    ]

    name = fields.Char(string='Producto', required=True, tracking=True)
    code = fields.Char(
        string='Código',
        required=True,
        copy=False,
        tracking=True,
        default=lambda self: _('Nuevo'),
    )
    barcode_preview_html = fields.Html(
        string='Código de Barras',
        compute='_compute_barcode_preview_html',
        sanitize=False,
    )
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    unit_id = fields.Many2one('uom.uom', string='Unidad', required=True)
    description = fields.Text(string='Descripción')
    brand_id = fields.Many2one('product.brand', string='Marca')
    model_name = fields.Char(string='Modelo')
    vendor_id = fields.Many2one(
        'res.partner',
        string='Proveedor Principal',
        domain=[('supplier_rank', '>', 0)],
    )
    unit_price = fields.Float(string='Precio Unitario', digits=(16, 2))
    tax_ids = fields.Many2many(
        'account.tax',
        'compras_product_tax_rel',
        'product_id',
        'tax_id',
        string='Impuestos',
    )
    move_ids = fields.One2many(
        'compras.inventory.move',
        'product_id',
        string='Movimientos',
    )
    qty_in = fields.Float(string='Entradas', compute='_compute_stock_quantities', store=True)
    qty_out = fields.Float(string='Salidas', compute='_compute_stock_quantities', store=True)
    qty_on_hand = fields.Float(string='Existencia Actual', compute='_compute_stock_quantities', store=True)
    last_entry_date = fields.Datetime(string='Última Entrada', compute='_compute_last_dates', store=True)
    last_exit_date = fields.Datetime(string='Última Salida', compute='_compute_last_dates', store=True)

    @api.depends('move_ids.state', 'move_ids.move_type', 'move_ids.quantity_done')
    def _compute_stock_quantities(self):
        for product in self:
            done_moves = product.move_ids.filtered(lambda m: m.state == 'done')
            qty_in = sum(done_moves.filtered(lambda m: m.move_type == 'entrada').mapped('quantity_done'))
            qty_out = sum(done_moves.filtered(lambda m: m.move_type == 'salida').mapped('quantity_done'))
            product.qty_in = qty_in
            product.qty_out = qty_out
            product.qty_on_hand = qty_in - qty_out

    @api.depends('move_ids.state', 'move_ids.move_type', 'move_ids.movement_date')
    def _compute_last_dates(self):
        for product in self:
            done_entries = product.move_ids.filtered(lambda m: m.state == 'done' and m.move_type == 'entrada')
            done_exits = product.move_ids.filtered(lambda m: m.state == 'done' and m.move_type == 'salida')
            product.last_entry_date = max(done_entries.mapped('movement_date')) if done_entries else False
            product.last_exit_date = max(done_exits.mapped('movement_date')) if done_exits else False

    @api.depends('code')
    def _compute_barcode_preview_html(self):
        for product in self:
            code = (product.code or '').strip()
            if not code:
                product.barcode_preview_html = '<span>Escanee o capture un codigo para previsualizar.</span>'
                continue

            product.barcode_preview_html = (
                '<div style="padding:8px; background:#fff; border:1px solid #ddd; display:inline-block;">'
                '<img alt="barcode" src="/report/barcode/Code128/%s?width=600&height=120&humanreadable=1" '
                'style="max-width:100%%; height:70px;"/>'
                '</div>'
            ) % code

    def name_get(self):
        result = []
        for product in self:
            if product.code:
                display_name = '[%s] %s' % (product.code, product.name)
            else:
                display_name = product.name
            result.append((product.id, display_name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Busca por nombre o código de barras."""
        args = args or []
        if name:
            search_domain = expression.AND([
                args,
                ['|', ('name', operator, name), ('code', operator, name)],
            ])
        else:
            search_domain = args
        products = self.search(search_domain, limit=limit)
        return products.name_get()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals.get('code') == _('Nuevo'):
                next_code = self.env['ir.sequence'].next_by_code('compras.product') or _('Nuevo')
                vals['code'] = self._normalize_auto_code(next_code)
        return super().create(vals_list)

    @api.model
    def _normalize_auto_code(self, code):
        """Normaliza el código autogenerado al formato numérico de 6 dígitos."""
        if not code or code == _('Nuevo'):
            return code

        match = re.search(r'(\d+)$', code.strip())
        if not match:
            return code

        return match.group(1).zfill(6)

