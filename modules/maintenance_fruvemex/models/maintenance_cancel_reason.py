from odoo import models, fields

# Catálogo reutilizable para Motivo de No Realización.
class MaintenanceCancelReason(models.Model):
    _name = 'fruve.maintenance.cancel.reason'
    _description = 'Motivo de No Realización'

    name = fields.Char(string='Motivo', required=True)
    active = fields.Boolean(default=True)

