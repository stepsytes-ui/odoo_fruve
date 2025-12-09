from odoo import fields, models

class HrArea(models.Model):
    _name = 'hr.area'
    _description = 'Área'

    name = fields.Char(string='Nombre del Área', required=True)
    department_id = fields.Many2one('hr.department', string='Departamento', required=True)
    employee_ids = fields.One2many('hr.employee', 'area_id', string='Empleados')
    employee_count = fields.Integer(string='Número de Empleados', compute='_compute_employee_count')

    def _compute_employee_count(self):
        for area in self:
            area.employee_count = len(area.employee_ids)

    _sql_constraints = [
        ('name_department_unique', 'unique(name, department_id)', 'El nombre del área debe ser único dentro del Departamento!'),
    ]