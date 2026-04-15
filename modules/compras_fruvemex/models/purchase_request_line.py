from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _description = 'Línea de Solicitud de Compra'

    request_id = fields.Many2one(
        'purchase.request',
        string='Solicitud de Compra',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        related='request_id.company_id',
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one('product.product', string='Producto Odoo')
    warehouse_product_id = fields.Many2one('compras.product', string='Producto')
    quantity = fields.Float(string='Cantidad', required=True, default=1.0)
    unit_id = fields.Many2one('uom.uom', string='Unidad', required=True)
    description = fields.Text(string='Descripción', required=True)
    brand_id = fields.Many2one('product.brand', string='Marca')
    model_name = fields.Char(string='Modelo')
    vendor_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        domain=[('supplier_rank', '>', 0)],
    )
    unit_price = fields.Float(string='Precio Unitario', digits=(16, 2))
    tax_ids = fields.Many2many(
        'account.tax',
        'purchase_request_line_tax_rel',
        'line_id',
        'tax_id',
        string='Impuestos',
    )
    received_qty = fields.Float(string='Cantidad Recibida', digits=(16, 2))
    receipt_status = fields.Selection(
        [
            ('completo', 'Completo'),
            ('incompleto', 'Incompleto'),
            ('faltante', 'Con Faltante'),
        ],
        string='Estado de Recepción',
        default='completo',
    )
    receipt_notes = fields.Text(string='Observaciones de Recepción')
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
        digits=(16, 2),
    )

    @api.onchange('warehouse_product_id')
    def _onchange_warehouse_product_id(self):
        if not self.warehouse_product_id:
            return
        product = self.warehouse_product_id
        self.description = product.description or product.name
        self.unit_id = product.unit_id
        self.brand_id = product.brand_id
        self.model_name = product.model_name
        self.unit_price = product.unit_price
        self.tax_ids = product.tax_ids
        self.vendor_id = product.vendor_id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id or self.warehouse_product_id:
            return
        tmpl = self.product_id.product_tmpl_id
        self.description = self.description or tmpl.description_purchase or tmpl.name
        self.unit_id = self.unit_id or tmpl.uom_id
        self.unit_price = self.unit_price or tmpl.list_price or tmpl.standard_price
        self.tax_ids = self.tax_ids or tmpl.taxes_id
        if tmpl.seller_ids and not self.vendor_id:
            self.vendor_id = tmpl.seller_ids[0].partner_id

    @api.onchange('quantity')
    def _onchange_quantity(self):
        if self.quantity and not self.received_qty:
            self.received_qty = self.quantity

    @api.constrains('quantity', 'received_qty')
    def _check_received_qty(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('La cantidad debe ser mayor a cero.'))
            if line.received_qty and line.received_qty > line.quantity:
                raise ValidationError(_('La cantidad recibida no puede ser mayor a la cantidad solicitada.'))

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price
