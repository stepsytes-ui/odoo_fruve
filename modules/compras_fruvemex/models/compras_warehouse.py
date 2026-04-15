from odoo import api, fields, models, _


class ComprasWarehouse(models.Model):
    _name = 'compras.warehouse'
    _description = 'Almacén'
    _order = 'company_id, name'

    name = fields.Char(string='Nombre del Almacén', required=True)
    code = fields.Char(string='Código', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
    )
    is_main = fields.Boolean(string='Almacén Principal', default=False)
    active = fields.Boolean(string='Activo', default=True)
    notes = fields.Text(string='Observaciones')
    source_move_ids = fields.One2many(
        'compras.inventory.move',
        'source_warehouse_id',
        string='Movimientos de Salida',
    )
    destination_move_ids = fields.One2many(
        'compras.inventory.move',
        'destination_warehouse_id',
        string='Movimientos de Entrada',
    )
    movement_count = fields.Integer(string='Movimientos', compute='_compute_movement_count')

    @api.depends('source_move_ids', 'destination_move_ids')
    def _compute_movement_count(self):
        for warehouse in self:
            warehouse.movement_count = len(warehouse.source_move_ids | warehouse.destination_move_ids)

    _sql_constraints = [
        ('code_company_unique', 'unique(code, company_id)', 'El código del almacén debe ser único por empresa.'),
    ]
