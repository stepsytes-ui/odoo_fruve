from odoo import fields, models, _
from odoo.exceptions import ValidationError


class PurchaseRejectionWizard(models.TransientModel):
    _name = 'purchase.rejection.wizard'
    _description = 'Wizard para rechazar solicitud de compra'

    request_id = fields.Many2one('purchase.request', string='Solicitud', required=True)
    rejection_reason = fields.Text(string='Motivo de Rechazo', required=True)
    add_comment = fields.Boolean(string='Agregar otros comentarios')
    decision_comments = fields.Text(string='Otros Comentarios')

    def action_confirm_rejection(self):
        self.ensure_one()
        if self.request_id.state != 'activa':
            raise ValidationError(_('Solo se pueden rechazar solicitudes en estado Activa.'))
        rejection_reason = (self.rejection_reason or '').strip()
        if not rejection_reason:
            raise ValidationError(_('Debes indicar el motivo del rechazo.'))
        decision_comments = (
            self.decision_comments.strip()
            if self.add_comment and self.decision_comments
            else False
        )
        self.request_id.write({
            'state': 'inactiva',
            'rejection_reason': rejection_reason,
            'rejected_by_id': self.env.user.id,
            'decision_comments': decision_comments,
            'decision_comment_user_id': self.env.user.id if decision_comments else False,
            'decision_comment_date': fields.Datetime.now() if decision_comments else False,
        })
        return {'type': 'ir.actions.act_window_close'}
