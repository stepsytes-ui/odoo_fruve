# -*- coding: utf-8 -*-

from odoo import fields, models


class ComprasMoveType(models.Model):
    _name = 'compras.move.type'
    _description = 'Tipo de Movimiento de Almacén'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(
        string='Código',
        required=True,
        help='Código técnico del tipo de movimiento (inicial, entrada, salida, transferencia)',
    )
    active = fields.Boolean(string='Activo', default=True)
    description = fields.Text(string='Descripción')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'El código del tipo de movimiento debe ser único.'),
    ]
