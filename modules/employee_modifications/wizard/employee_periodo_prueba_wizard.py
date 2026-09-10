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
            ('no_renovacion', 'No renovación'),
        ],
        string='Resolución',
        required=True,
        default='indefinido',
    )
    motivo_no_renovacion = fields.Text(string='Motivo de No Renovación')

    def action_confirm(self):
        self.ensure_one()
        employee = self.employee_id.exists()
        if not employee:
            raise ValidationError(_('El empleado ya no existe.'))

        if self.decision == 'no_renovacion':
            if not self.motivo_no_renovacion or not self.motivo_no_renovacion.strip():
                raise ValidationError(_('Debe capturar el motivo de la no renovación.'))
            employee.write({
                'periodo_prueba': False,
                'periodo_prueba_fecha_inicio': False,
                'periodo_prueba_alerta_enviada': False,
                'contrato_no_renovado': True,
                'fecha_no_renovacion': fields.Date.today(),
                'motivo_no_renovacion': self.motivo_no_renovacion.strip(),
            })
        elif self.decision == 'indefinido':
            employee.write({
                'periodo_prueba': False,
                'periodo_prueba_fecha_inicio': False,
                'periodo_prueba_alerta_enviada': False,
                'contrato_no_renovado': False,
                'fecha_no_renovacion': False,
                'motivo_no_renovacion': False,
            })
        else:
            fecha_inicio = employee.fecha_fin_periodo_prueba or fields.Date.today()
            fecha_inicio = max(fecha_inicio, date.today())
            employee.write({
                'periodo_prueba': self.decision,
                'periodo_prueba_fecha_inicio': fecha_inicio,
                'periodo_prueba_alerta_enviada': False,
                'contrato_no_renovado': False,
                'fecha_no_renovacion': False,
                'motivo_no_renovacion': False,
            })

        return {'type': 'ir.actions.act_window_close'}
