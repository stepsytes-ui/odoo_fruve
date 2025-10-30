# -*- coding: utf-8 -*-

from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    device_ids = fields.One2many(
        'zkteco.device',
        'company_id',
        string='Dispositivos Checadores'
    )