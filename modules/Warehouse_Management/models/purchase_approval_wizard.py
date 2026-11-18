from odoo import fields, models


class PurchaseApprovalWizard(models.TransientModel):
    _name = 'purchase.approval.wizard'
    _description = 'Confirmación de aprobación de orden de compra'

    request_id = fields.Many2one(
        'purchase.request',
        string='Solicitud',
        required=True,
    )
    add_comment = fields.Boolean(string='Agregar otros comentarios')
    decision_comments = fields.Text(string='Otros Comentarios')

    def action_confirm_approval(self):
        self.ensure_one()
        self.request_id._approve_with_comments(
            self.decision_comments if self.add_comment else False
        )
        return {'type': 'ir.actions.act_window_close'}
