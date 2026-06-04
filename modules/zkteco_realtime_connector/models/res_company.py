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

    attendance_reports_base_url = fields.Char(
        string='URL Base Reportes RH',
        help='URL opcional para enlaces de reportes/alertas de asistencia. '
             'Si no se define, se usa web.base.url del sistema.'
    )
    
    def _get_timezone_selection(self):
        """Devuelve lista de zonas horarias disponibles"""
        import pytz
        return [(tz, tz) for tz in pytz.all_timezones]

    def get_attendance_reports_base_url(self):
        self.ensure_one()
        base_url = (
            self.attendance_reports_base_url
            or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            or ''
        )
        return base_url.rstrip('/')