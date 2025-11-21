# -*- coding: utf-8 -*-
from odoo import models, fields, api


class security_view(models.Model):
    _inherit = 'hr.leave' 

    biometric_id = fields.Char(
        string='No. Empleado',
        related='employee_id.biometric_id',
        store=True,
        readonly=True
    )

    description_security = fields.Text(
        string='Motivo Visible',
        compute='_compute_description_security',
        store=False,
        readonly=True
    )

    @api.depends('name')
    def _compute_description_security(self):
        """ Copia el valor del campo 'name' usando sudo para evadir FLS. """
        for record in self:
            # USAMOS SUDO() para asegurarnos de que el código puede leer el campo 'name' 
            # antes de asignarlo al campo 'description_security' visible.
            if record.name:
                record.description_security = record.sudo().name
            else:
                record.description_security = False


