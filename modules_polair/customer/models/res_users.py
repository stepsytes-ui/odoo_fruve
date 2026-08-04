from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    default_custom_tax_option_id = fields.Many2one(
        'customer.tax.option',
        string='Opcion de impuesto por defecto',
    )

    default_custom_tax_percent = fields.Float(
        string='Impuesto por defecto (%)',
        digits=(16, 2),
        default=16.0,
        help='Porcentaje de impuesto usado por defecto en nuevas lineas de venta.',
    )
