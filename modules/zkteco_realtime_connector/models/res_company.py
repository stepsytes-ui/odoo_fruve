# -*- coding: utf-8 -*-

from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    device_ids = fields.One2many(
        'zkteco.device',
        'company_id',
        string='Dispositivos Checadores'
    )
    
    timezone = fields.Selection(
        selection='_get_timezone_selection',
        string='Zona Horaria de la Empresa',
        default='America/Tijuana',
        help='Zona horaria utilizada para las checadas de asistencia de esta empresa'
    )
    
    def _get_timezone_selection(self):
        """Devuelve lista de zonas horarias disponibles"""
        import pytz
        return [(tz, tz) for tz in pytz.all_timezones]