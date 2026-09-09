from datetime import date

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class EmployeePeriodoPruebaWizard(models.TransientModel):
    _name = 'employee.periodo.prueba.wizard'
    _description = 'Resolver periodo de prueba del empleado'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        readonly=True,
    )
    decision = fields.Selection(
        [
            ('30', 'Renovar 30 días'),
            ('60', 'Renovar 60 días'),
            ('90', 'Renovar 90 días'),
            ('180', 'Renovar 180 días'),
            ('indefinido', 'Marcar como indefinido'),
        ],
        string='Resolución',
        required=True,
        default='indefinido',
    )

    def action_confirm(self):
        self.ensure_one()
        employee = self.employee_id.exists()
        if not employee:
            raise ValidationError(_('El empleado ya no existe.'))

        if self.decision == 'indefinido':
            employee.write({
                'periodo_prueba': False,
                'periodo_prueba_fecha_inicio': False,
                'periodo_prueba_alerta_enviada': False,
            })
        else:
            fecha_inicio = employee.fecha_fin_periodo_prueba or fields.Date.today()
            fecha_inicio = max(fecha_inicio, date.today())
            employee.write({
                'periodo_prueba': self.decision,
                'periodo_prueba_fecha_inicio': fecha_inicio,
                'periodo_prueba_alerta_enviada': False,
            })

        return {'type': 'ir.actions.act_window_close'}
