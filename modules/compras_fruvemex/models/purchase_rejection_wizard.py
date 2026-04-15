from odoo import fields, models


class PurchaseRejectionWizard(models.TransientModel):
    _name = 'purchase.rejection.wizard'
    _description = 'Wizard para rechazar solicitud de compra'

    request_id = fields.Many2one('purchase.request', string='Solicitud', required=True)
    rejection_reason = fields.Text(string='Motivo de Rechazo', required=True)

    def action_confirm_rejection(self):
        self.ensure_one()
        self.request_id.write({
            'state': 'inactiva',
            'rejection_reason': self.rejection_reason,
            'rejected_by_id': self.env.user.id,
        })
        return {'type': 'ir.actions.act_window_close'}
