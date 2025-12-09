from odoo import models,fields


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    daily_rate = fields.Float(string="Salario Diario")
    area_id = fields.Many2one('hr.area', string='Área')