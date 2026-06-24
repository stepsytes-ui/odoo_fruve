import re
import math

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import float_is_zero


class ComprasProductCategory(models.Model):
    _name = 'compras.product.category'
    _description = 'Categoria de Consolidado'
    _order = 'name'

    name = fields.Char(string='Categoria', required=True)

    _sql_constraints = [
        ('compras_product_category_name_unique', 'unique(name)', 'La categoria ya existe.'),
    ]


class ComprasProductSubcategory(models.Model):
    _name = 'compras.product.subcategory'
    _description = 'Subcategoria de Consolidado'
    _order = 'category_id, name'

    name = fields.Char(string='Subcategoria', required=True)
    category_id = fields.Many2one('compras.product.category', string='Categoria', required=True, ondelete='cascade')

    _sql_constraints = [
        (
            'compras_product_subcategory_unique',
            'unique(name, category_id)',
            'La subcategoria ya existe en esta categoria.',
        ),
    ]


class ComprasRepairLine(models.Model):
    _name = 'compras.repair.line'
    _description = 'Equipo - Linea a Reparar'
    _order = 'name'

    name = fields.Char(string='Equipo - Linea a Reparar', required=True)

    _sql_constraints = [
        ('compras_repair_line_name_unique', 'unique(name)', 'La linea a reparar ya existe.'),
    ]


class ComprasProduct(models.Model):
    _name = 'compras.product'
    _description = 'Consolidado de Productos'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _sql_constraints = [
        ('compras_product_code_unique', 'unique(code)', 'El código del producto debe ser único.'),
    ]

    name = fields.Char(string='Descripcion', required=True, tracking=True)
    code = fields.Char(
        string='Código',
        required=True,
        copy=False,
        tracking=True,
        default=lambda self: _('Nuevo'),
    )
    serial = fields.Char(string='Serial')
    manufacturer = fields.Char(string='Fabricante')
    classification = fields.Char(string='Clasificacion')
    category_id = fields.Many2one('compras.product.category', string='Categoria')
    subcategory_id = fields.Many2one(
        'compras.product.subcategory',
        string='Subcategoria',
        domain="[('category_id', '=', category_id)]",
    )
    subcategory_2 = fields.Char(string='Sub-Categoria 2')
    location = fields.Char(string='Locacion')
    expiration_date = fields.Date(string='Fecha de Caducidad')
    is_chemical_category = fields.Boolean(compute='_compute_is_chemical_category')
    repair_line_id = fields.Many2one('compras.repair.line', string='Equipo - Linea a Reparar')
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
    description = fields.Text(string='Notas')
    brand_id = fields.Many2one('product.brand', string='Marca')
    model_name = fields.Char(string='Modelo')
    qty_process = fields.Float(string='Qty - Proceso', digits=(16, 2))
    total_equipment = fields.Float(string='Total Equipos', digits=(16, 2))
    total_qty_process = fields.Float(
        string='Total Qty Proceso',
        compute='_compute_total_qty_process',
        store=True,
        digits=(16, 2),
    )
    frequency_use_days = fields.Float(string='Frecuencia Uso Dias', digits=(16, 2))
    lead_time_days = fields.Float(string='Tiempo de Entrega (Dias)', digits=(16, 2))
    purchase_type = fields.Selection(
        [
            ('local', 'Local'),
            ('internacional', 'Internacional'),
        ],
        string='Tipo de Compra',
        default='local',
        required=True,
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Proveedor Principal',
        domain=['|', ('supplier_rank', '>', 0), ('compras_product_ids', '!=', False)],
    )
    unit_price = fields.Float(string='Precio Unitario', digits=(16, 2))
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    total_cost = fields.Float(
        string='Costo Total',
        compute='_compute_total_cost',
        store=True,
        digits=(16, 2),
    )
    coverage_days = fields.Float(
        string='Cobertura (Dias)',
        compute='_compute_planning_metrics',
        store=True,
        digits=(16, 2),
    )
    min_qty = fields.Float(string='MIN', digits=(16, 0))
    reorder_point = fields.Float(
        string='Punto Reorden',
        compute='_compute_planning_metrics',
        store=True,
        digits=(16, 0),
    )
    max_qty = fields.Float(
        string='MAX',
        compute='_compute_planning_metrics',
        store=True,
        digits=(16, 0),
    )
    monthly_budget = fields.Float(
        string='Presupuesto Mensual',
        compute='_compute_monthly_budget',
        store=True,
        digits=(16, 2),
    )
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
    qty_on_hand = fields.Float(
        string='Inventario',
        compute='_compute_stock_quantities',
        inverse='_inverse_qty_on_hand',
        store=True,
    )
    last_entry_date = fields.Datetime(string='Última Entrada', compute='_compute_last_dates', store=True)
    last_exit_date = fields.Datetime(string='Última Salida', compute='_compute_last_dates', store=True)

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.subcategory_id and self.subcategory_id.category_id != self.category_id:
            self.subcategory_id = False

    @api.onchange('min_qty', 'total_qty_process', 'frequency_use_days', 'lead_time_days')
    def _onchange_planning_inputs(self):
        for product in self:
            product.reorder_point = product.min_qty or 0.0
            if product.total_qty_process > 0 and product.frequency_use_days > 0:
                daily_demand = product.total_qty_process / product.frequency_use_days
                product.max_qty = product.reorder_point + math.ceil(daily_demand * product.lead_time_days)
            else:
                product.max_qty = product.reorder_point

    @api.depends('category_id', 'category_id.name')
    def _compute_is_chemical_category(self):
        for product in self:
            category_name = (product.category_id.name or '').strip().lower()
            normalized = (
                category_name
                .replace('á', 'a')
                .replace('é', 'e')
                .replace('í', 'i')
                .replace('ó', 'o')
                .replace('ú', 'u')
            )
            product.is_chemical_category = normalized.startswith('quimic')

    @api.constrains('qty_process', 'total_equipment', 'frequency_use_days', 'lead_time_days')
    def _check_positive_numbers(self):
        for product in self:
            if product.qty_process < 0 or product.total_equipment < 0:
                raise ValidationError(_('Qty - Proceso y Total Equipos no pueden ser negativos.'))
            if product.frequency_use_days < 0 or product.lead_time_days < 0:
                raise ValidationError(_('Frecuencia de uso y tiempo de entrega no pueden ser negativos.'))

    @api.depends('qty_process', 'total_equipment')
    def _compute_total_qty_process(self):
        for product in self:
            product.total_qty_process = product.total_equipment * product.qty_process

    @api.depends('unit_price', 'qty_on_hand')
    def _compute_total_cost(self):
        for product in self:
            product.total_cost = product.unit_price * product.qty_on_hand

    @api.depends('min_qty', 'qty_on_hand', 'total_qty_process', 'frequency_use_days', 'lead_time_days')
    def _compute_planning_metrics(self):
        for product in self:
            product.reorder_point = product.min_qty or 0.0
            if product.total_qty_process > 0 and product.frequency_use_days > 0:
                daily_demand = product.total_qty_process / product.frequency_use_days
                product.coverage_days = (product.qty_on_hand / product.total_qty_process) * product.frequency_use_days
                product.max_qty = product.reorder_point + math.ceil(daily_demand * product.lead_time_days)
            else:
                product.coverage_days = 0.0
                product.max_qty = product.reorder_point

    @api.depends('total_qty_process', 'frequency_use_days', 'unit_price')
    def _compute_monthly_budget(self):
        for product in self:
            if product.frequency_use_days > 0:
                product.monthly_budget = ((product.total_qty_process / product.frequency_use_days) * 30.0) * product.unit_price
            else:
                product.monthly_budget = 0.0

    @api.depends('move_ids.state', 'move_ids.move_type', 'move_ids.quantity_done')
    def _compute_stock_quantities(self):
        for product in self:
            done_moves = product.move_ids.filtered(lambda m: m.state == 'done')
            qty_in = sum(done_moves.filtered(lambda m: m.move_type == 'entrada').mapped('quantity_done'))
            qty_out = sum(done_moves.filtered(lambda m: m.move_type == 'salida').mapped('quantity_done'))
            product.qty_in = qty_in
            product.qty_out = qty_out
            product.qty_on_hand = qty_in - qty_out

    def _inverse_qty_on_hand(self):
        move_model = self.env['compras.inventory.move']
        for product in self:
            done_moves = product.move_ids.filtered(lambda move: move.state == 'done')
            current_qty = (
                sum(done_moves.filtered(lambda move: move.move_type == 'entrada').mapped('quantity_done'))
                - sum(done_moves.filtered(lambda move: move.move_type == 'salida').mapped('quantity_done'))
            )
            target_qty = product.qty_on_hand
            delta = target_qty - current_qty
            rounding = product.unit_id.rounding if product.unit_id else 0.01

            if float_is_zero(delta, precision_rounding=rounding):
                continue

            if delta < 0:
                raise ValidationError(_(
                    'No se puede reducir Inventario desde este campo. Usa una salida de almacen para disminuir existencias.'
                ))

            adjustment_move = move_model.create({
                'company_id': product.company_id.id,
                'move_type': 'entrada',
                'product_id': product.id,
                'quantity': delta,
                'quantity_done': delta,
                'status': 'completo',
                'receiver_name': _('Inventario inicial'),
                'destination': _('Ajuste de inventario existente'),
                'notes': _('Entrada creada automaticamente por ajuste manual de Inventario en Consolidado.'),
            })
            adjustment_move.action_confirm()

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

