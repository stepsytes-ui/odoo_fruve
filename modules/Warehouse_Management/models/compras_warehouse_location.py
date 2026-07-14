from odoo import fields, models


class ComprasWarehouseLocation(models.Model):
    _name = 'compras.warehouse.location'
    _description = 'Locación de Almacén'
    _order = 'warehouse_id, name'

    name = fields.Char(string='Locación', required=True)
    warehouse_id = fields.Many2one(
        'compras.warehouse',
        string='Almacén',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        related='warehouse_id.company_id',
        store=True,
        readonly=True,
    )
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        (
            'compras_warehouse_location_unique',
            'unique(name, warehouse_id)',
            'La locación ya existe en este almacén.',
        ),
    ]
