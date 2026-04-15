from odoo import fields, models


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Marca de Producto'

    name = fields.Char(string='Nombre de Marca', required=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'El nombre de la marca debe ser único.'),
    ]
