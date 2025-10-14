
from odoo import models,fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_teacher = fields.Boolean(string='Is teacher')
    is_student = fields.Boolean(string='Is student')
    is_freelance = fields.Boolean(string='Is freelance')
