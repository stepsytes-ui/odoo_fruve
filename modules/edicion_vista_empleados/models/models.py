# -*- coding: utf-8 -*-
from odoo import models, fields, api


class edicion_vista_empleados(models.Model):
    _inherit = 'hr.employee'

    # Campos nuevos
    mi_campo_nuevo = fields.Char(string='Mi Nuevo campo personalizado', required=True)
    number1 = fields.Integer(string='Introduce el primer numero')
    number2 = fields.Integer(string='Introduce el segundo numero')
    result = fields.Integer(
        string='Resultado',
        compute='_suma_de_valores',
        store=False,
    )
    
    # Campos existentes
    work_email = fields.Char(require=True)

    @api.depends('number1','number2')
    def _suma_de_valores(self):

        for record in self:
            record.result = record.number1 + record.number2
    
        