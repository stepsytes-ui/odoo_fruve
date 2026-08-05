from odoo import models, fields

# Catálogo reutilizable de Tipos de Mantenimiento.
class MaintenanceType(models.Model):
    _name = 'fruve.maintenance.type'
    _description = 'Tipo de Mantenimiento'

    name = fields.Char(string='Nombre', required=True)
    active = fields.Boolean(default=True)