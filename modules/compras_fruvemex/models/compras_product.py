from odoo import api, fields, models, _


class ComprasProduct(models.Model):
    _name = 'compras.product'
    _description = 'Producto de Almacén'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Producto', required=True, tracking=True)
    code = fields.Char(
        string='Código',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo'),
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', _('Nuevo')) == _('Nuevo'):
                vals['code'] = self.env['ir.sequence'].next_by_code('compras.product') or _('Nuevo')
        return super().create(vals_list)
