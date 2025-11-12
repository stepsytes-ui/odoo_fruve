
from odoo import models, fields, api

class EmployeeExpedientReingresoWizard(models.TransientModel):
    _name = 'employee.expedient.reingreso.wizard'
    _description = 'Asistente para registro de Reingreso de Expediente'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, readonly=True)
    fecha_movimiento = fields.Date(string='Fecha de Movimiento', required=True, default=fields.Date.today)

    
    # Acción para crear el registro de baja
    def action_confirm_reingreso(self):
        self.ensure_one()
        
        # 1. Crear el registro de Expediente (tipo baja)
        expedient = self.env['employee.expedient'].create({
            'employee_id': self.employee_id.id,
            'tipo_registro': 'reingreso',
            'fecha_movimiento': self.fecha_movimiento,
            'recontratable': 'n/a',
        })

        self.employee_id.write({'employee_status': 'active'})

        return {'type': 'ir.actions.act_window_close'}