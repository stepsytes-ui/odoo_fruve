from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    compras_product_ids = fields.One2many(
        'compras.product',
        'vendor_id',
        string='Productos Consolidado',
    )
