# -*- coding: utf 8 -*-
from odoo import models, fields, api

DEFAULT_BACKWARD_ADJUSTMENT_SERIALS = ('AEWU174160316',)

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

    time_adjustment_enabled = fields.Boolean(
        string='Ajustar hora del checador',
        help='Activa la corrección de una hora para las checadas recibidas de este dispositivo.'
    )

    time_adjustment_direction = fields.Selection(
        selection=[
            ('backward', 'Atrasar una hora'),
            ('forward', 'Adelantar una hora'),
        ],
        string='Ajuste de hora',
        default='backward',
        required=True,
        help='Sentido de la corrección aplicada al timestamp enviado por el checador.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('serial_number') in DEFAULT_BACKWARD_ADJUSTMENT_SERIALS:
                vals.setdefault('time_adjustment_enabled', True)
                vals.setdefault('time_adjustment_direction', 'backward')
        return super().create(vals_list)

    @api.model
    def configure_default_time_adjustments(self):
        devices = self.sudo().search([
            ('serial_number', 'in', DEFAULT_BACKWARD_ADJUSTMENT_SERIALS),
        ])
        if devices:
            devices.write({
                'time_adjustment_enabled': True,
                'time_adjustment_direction': 'backward',
            })
        return True
