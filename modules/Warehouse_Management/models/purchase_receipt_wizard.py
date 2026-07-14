from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseReceiptWizard(models.TransientModel):
    _name = 'purchase.receipt.wizard'
    _description = 'Checklist de Recepción de Compra'

    request_id = fields.Many2one('purchase.request', string='Solicitud', required=True)
    warehouse_id = fields.Many2one('compras.warehouse', string='Almacén', required=True)
    location_id = fields.Many2one(
        'compras.warehouse.location',
        string='Locación',
        domain="[('warehouse_id', '=', warehouse_id)]",
    )
    receiver_user_id = fields.Many2one('res.users', string='Recibe', default=lambda self: self.env.user, required=True)
    line_ids = fields.One2many('purchase.receipt.wizard.line', 'wizard_id', string='Checklist')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        request = self.env['purchase.request'].browse(self.env.context.get('default_request_id'))
        if request:
            res['warehouse_id'] = request.warehouse_id.id
            default_location = self.env['compras.warehouse.location'].search([
                ('warehouse_id', '=', request.warehouse_id.id),
                ('active', '=', True),
            ], limit=1)
            res['location_id'] = default_location.id if default_location else False
            res['line_ids'] = [(0, 0, {
                'request_line_id': line.id,
                'product_id': line.warehouse_product_id.id,
                'quantity_expected': line.quantity,
                'quantity_received': line.quantity,
                'receipt_check': 'completo',
                'notes': line.receipt_notes or '',
            }) for line in request.line_ids]
        return res

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        for wizard in self:
            if wizard.location_id and wizard.location_id.warehouse_id != wizard.warehouse_id:
                wizard.location_id = False

    def action_confirm_receipt(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_('No hay líneas para recibir.'))
        if self.location_id and self.location_id.warehouse_id != self.warehouse_id:
            raise ValidationError(_('La locación seleccionada debe pertenecer al almacén elegido.'))

        for wizard_line in self.line_ids:
            if wizard_line.quantity_received < 0:
                raise ValidationError(_('La cantidad recibida no puede ser negativa.'))
            if wizard_line.quantity_received > wizard_line.quantity_expected:
                raise ValidationError(_('La cantidad recibida no puede ser mayor a la esperada.'))
            if wizard_line.receipt_check != 'completo' and not wizard_line.notes:
                raise ValidationError(_('Debes escribir observaciones cuando existan faltantes o no llegue el material.'))

            request_line = wizard_line.request_line_id
            request_line.received_qty = wizard_line.quantity_received
            request_line.receipt_status = wizard_line.receipt_check
            request_line.receipt_notes = wizard_line.notes

        self.request_id.action_process_receipt_from_checklist(self.receiver_user_id, self.warehouse_id, self.location_id)
        return {'type': 'ir.actions.act_window_close'}


class PurchaseReceiptWizardLine(models.TransientModel):
    _name = 'purchase.receipt.wizard.line'
    _description = 'Línea Checklist de Recepción'

    wizard_id = fields.Many2one('purchase.receipt.wizard', string='Wizard', required=True, ondelete='cascade')
    request_line_id = fields.Many2one('purchase.request.line', string='Línea de Solicitud', required=True)
    product_id = fields.Many2one(
        'compras.product',
        string='Producto',
        related='request_line_id.warehouse_product_id',
        readonly=True,
    )
    quantity_expected = fields.Float(
        string='Cantidad Esperada',
        related='request_line_id.quantity',
        readonly=True,
    )
    quantity_received = fields.Float(string='Cantidad Recibida', required=True)
    receipt_check = fields.Selection([
        ('completo', 'Llegó completo'),
        ('incompleto', 'Llegó incompleto'),
        ('defectuoso', 'Llegó defectuoso'),
        ('faltante', 'No llegó / faltante'),
    ], string='Checklist', default='completo', required=True)
    notes = fields.Text(string='Observaciones')

    @api.onchange('receipt_check')
    def _onchange_receipt_check(self):
        if self.receipt_check == 'completo':
            self.quantity_received = self.quantity_expected
        elif self.receipt_check == 'faltante':
            self.quantity_received = 0
