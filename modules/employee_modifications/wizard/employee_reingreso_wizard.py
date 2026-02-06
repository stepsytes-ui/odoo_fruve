
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
            # 2. Agregar la "Baja" al historial (la matriz)
            self.env['employee.expedient.line'].create({
                'expedient_id': expedient.id,
                'tipo_movimiento': 'reingreso',
                'fecha': self.fecha_movimiento,
            })
            
            # 3. Guardar los archivos en el expediente maestro
            expedient.write({
                'tipo_registro': 'reingreso',
                'employee_status': 'active',
                'fecha_movimiento': self.fecha_movimiento,
            })

        self.employee_id.write({
            'active': True,
            'employee_status': 'active',
            'finiquitado': False,  # Quitar la marca de finiquitado
        })
        return {'type': 'ir.actions.act_window_close'}