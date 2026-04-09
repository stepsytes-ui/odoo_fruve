from odoo import fields, models


class AttendanceLateWeeklyAdjustment(models.Model):
    _name = 'attendance.late.weekly.adjustment'
    _description = 'Ajuste Manual Semanal de Retardos'
    _order = 'custom_year desc, custom_week desc, employee_id asc'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade')
    custom_year = fields.Integer(string='Anio', required=True)
    custom_week = fields.Integer(string='Semana', required=True)

    manual_total_late_minutes = fields.Integer(string='Minutos de Retardo (Manual)')
    manual_daily_minutes_json = fields.Text(string='Detalle Diario de Retardos (Manual)')
    manual_payable_days = fields.Float(string='Dias a Pagar (Manual)', digits=(16, 2))
    manual_observation = fields.Text(string='Observaciones (Manual)')

    _sql_constraints = [
        (
            'attendance_late_weekly_adjustment_unique',
            'unique(employee_id, custom_year, custom_week)',
            'Ya existe un ajuste para este empleado en esa semana.',
        ),
    ]
