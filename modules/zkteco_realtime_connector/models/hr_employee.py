
from odoo import models, fields, api


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    biometric_id = fields.Char(string='Numero de empleado')
    
    biometric_id_numeric = fields.Integer(
        string='Número de Empleado (Numérico)',
        compute='_compute_biometric_id_numeric',
        store=True,
        help='Campo numérico derivado de biometric_id para ordenamiento'
    )
    
    employee_status = fields.Selection([
        ('active', 'Activo'),
        ('inactive', 'Inactivo')
    ], string='Estado del Empleado', default='active', required=True, readonly=True)

    turno_id = fields.Many2one(
        comodel_name='shift.management',
        string='Turno Asignado',
        help='Selecciona el turno definido en la gestión de turnos.'
    )

    @api.depends('biometric_id')
    def _compute_biometric_id_numeric(self):
        """Convierte biometric_id a valor numérico para ordenamiento"""
        for employee in self:
            if employee.biometric_id and employee.biometric_id.isdigit():
                employee.biometric_id_numeric = int(employee.biometric_id)
            else:
                employee.biometric_id_numeric = 0
