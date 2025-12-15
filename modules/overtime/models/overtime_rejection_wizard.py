from odoo import api, fields, models

class OvertimeRejectionWizard(models.TransientModel):
    _name = 'overtime.rejection.wizard'
    _description = 'Wizard para rechazar solicitud de tiempo extra'

    overtime_id = fields.Many2one('overtime', string='Solicitud', required=True)
    rejection_reason = fields.Text(string='Motivo de Rechazo', required=True)

    def action_confirm_rejection(self):
        self.ensure_one()
        self.overtime_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
            'authorized_by_id': self.env.user.id
        })
        return {'type': 'ir.actions.act_window_close'}