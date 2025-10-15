
from odoo import models,fields


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    biometric_id = fields.Char(string='Biometric ID')
