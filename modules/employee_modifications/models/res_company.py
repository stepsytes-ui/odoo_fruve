# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    carta_laboral_name = fields.Char(
        string='Nombre de la empresa para carta laboral',
        help='Nombre que se mostrará en la carta laboral. Si se deja vacío, se usará el nombre de la compañía.'
    )

    carta_laboral_responsable_rh = fields.Many2one(
        'hr.employee',
        string='Responsable de RH (Carta Laboral)',
        domain="[('company_id', '=', id)]",
        help='Empleado cuyo nombre aparecerá como responsable de Recursos Humanos en la carta laboral.'
    )

    def get_carta_laboral_responsable_rh(self):
        self.ensure_one()
        if self.carta_laboral_responsable_rh:
            return self.carta_laboral_responsable_rh.name.upper()
        return 'RESPONSABLE DE RECURSOS HUMANOS'

    def get_carta_laboral_name(self):
        self.ensure_one()
        return self.carta_laboral_name or self.name or ''

    def get_carta_laboral_location(self):
        self.ensure_one()
        location_parts = []

        if self.city:
            location_parts.append(self.city.strip().upper())

        if self.state_id and self.state_id.name:
            location_parts.append(self.state_id.name.strip().upper())

        if location_parts:
            return ', '.join(location_parts)

        if self.country_id and self.country_id.name:
            return self.country_id.name.strip().upper()

        return ''