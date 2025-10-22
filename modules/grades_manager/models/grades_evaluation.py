
from odoo import models,fields

class GradesEvaluation(models.Model):
    _name = 'grades.evaluation'
    _description = 'Grades Evaluation'

    name = fields.Char(string='Name')
    date = fields.Date(string='Date')
    observations = fields.Text(string='Observations')

