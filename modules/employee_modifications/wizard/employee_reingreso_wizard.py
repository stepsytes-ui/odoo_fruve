
from odoo import models, fields, api

class EmployeeExpedientReingresoWizard(models.TransientModel):
    _name = 'employee.expedient.reingreso.wizard'
    _description = 'Asistente para registro de Reingreso de Expediente'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, readonly=True)
    fecha_movimiento = fields.Date(string='Fecha de Movimiento', required=True, default=fields.Date.today)

    def action_confirm_reingreso(self):
        self.ensure_one()
        expedient = self.env['employee.expedient'].search([('employee_id', '=', self.employee_id.id)], limit=1)
        
        if expedient:
            expedient._registrar_movimiento(
                'reingreso',
                self.fecha_movimiento,
                motivo='Reingreso del empleado',
                user_id=self.env.user.id,
            )
            
            expedient.write({
                'employee_status': 'active',
            })

        self.employee_id.write({
            'active': True,
            'employee_status': 'active',
            'finiquitado': False,  # Quitar la marca de finiquitado
        })
        return {'type': 'ir.actions.act_window_close'}