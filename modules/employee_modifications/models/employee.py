
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class HrEmployeeExtension(models.Model):
    _inherit = 'hr.employee'
    
    expedient_ids = fields.One2many(
        'employee.expedient', 
        'employee_id', 
        string='Historial de Movimientos'
    )

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        for employee in employees:
            self.env['employee.expedient'].create({
                    'employee_id': employee.id,
                    'tipo_registro': 'alta',
                    'fecha_movimiento': fields.Date.today(),
                    'recontratable': 'n/a',
                })
        return employees
    
    def action_open_expedient_baja_wizard(self):
        self.ensure_one()
        _logger.info("🟢 Abriendo wizard de baja para el empleado %s", self.name)
        return {
            'name': "Registro de Baja de empleado",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.expedient.baja.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('employee_modifications.view_employee_expedient_baja_wizard_form').id,
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }
    
    def action_open_expedient_reingreso_wizard(self):
        self.ensure_one()
        _logger.info("🟢 Abriendo wizard de reingreso para el empleado %s", self.name)
        return {
            'name': "Registro de Reingreso de empleado",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.expedient.reingreso.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('employee_modifications.view_employee_expedient_reingreso_wizard_form').id,
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }

