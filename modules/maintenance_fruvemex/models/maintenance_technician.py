from odoo import models, fields

# Catálogo de empleados designados como Técnicos.
class MaintenanceTechnician(models.Model):
    _name = 'fruve.maintenance.technician'
    _description = 'Técnico de Mantenimiento'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    active = fields.Boolean(default=True)
