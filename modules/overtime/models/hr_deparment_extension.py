
from odoo import models,fields

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    area_ids = fields.One2many(
        'hr.area', 
        'department_id', 
        string='Áreas'
    )