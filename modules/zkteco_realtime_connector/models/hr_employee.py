
from odoo import models,fields


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    biometric_id = fields.Char(string='Numero de empleado')
    
    employee_status = fields.Selection([
        ('active', 'Activo'),
        ('inactive', 'Inactivo')
    ], string='Estado del Empleado', default='active', required=True)

    turno_id = fields.Many2one(
        comodel_name='shift.management',
        string='Turno Asignado',
        help='Selecciona el turno definido en la gestión de turnos.'
    )
