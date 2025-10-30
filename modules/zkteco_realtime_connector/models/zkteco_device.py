# -*- coding: utf 8 -*-
from odoo import models, fields, api

class ZkTecoDevice(models.Model):

    _name = 'zkteco.device'
    _description = 'Checadores de cada sucursal'
    _sql_constraints = [
       ('serial_number_uniq','unique(serial_number)',
        'El número de serie del dispositivo debe ser único.') 
    ]

    name = fields.Char(
        string='Nombre del checador',
        required=True,
        help='Este es el ID (S/N) que el dispositivo envial al servidor.'
    )

    serial_number = fields.Char(
        string='Número de serie (Device ID)',
        required=True,
        help="Este es el ID (S/N) que el dispositivio envía al servidor."
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compañia',
        required=True,
        default=lambda self: self.env.company,
        help="Compañia a la que pertenece este dispositivo."
    )

    location = fields.Char(
        string='Ubicacion',
        help="Campo opcional para describir la ubicación física."
    )