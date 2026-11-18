from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize


class PurchaseOrderConfigWizard(models.TransientModel):
    _name = 'purchase.order.config.wizard'
    _description = 'Configuración de órdenes de compra'

    invoice_email = fields.Char(
        string='Correo para facturas',
        required=True,
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'Warehouse_Management.purchase_order_invoice_email',
            'cuentasporpagarmxl@fruvemex.com',
        ),
    )

    def action_save(self):
        self.ensure_one()
        email = email_normalize(self.invoice_email)
        if not email:
            raise ValidationError(_('Ingresa una dirección de correo válida.'))
        self.env['ir.config_parameter'].sudo().set_param(
            'Warehouse_Management.purchase_order_invoice_email',
            email,
        )
        return {'type': 'ir.actions.act_window_close'}
