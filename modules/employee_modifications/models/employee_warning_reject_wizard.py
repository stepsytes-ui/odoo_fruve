# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class EmployeeWarningRejectWizard(models.TransientModel):
    _name = 'employee.warning.reject.wizard'
    _description = 'Wizard para Rechazar Amonestación'

    warning_id = fields.Many2one(
        'employee.warning',
        string='Amonestación',
        required=True
    )

    rejection_reason = fields.Text(
        string='Motivo del Rechazo',
        required=True,
        placeholder='Ingrese el motivo por el cual se rechaza esta amonestación...'
    )

    def action_reject(self):
        """Rechazar la amonestación con el motivo ingresado"""
        self.warning_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason
        })
        return {'type': 'ir.actions.act_window_close'}
