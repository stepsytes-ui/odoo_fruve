from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


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
            'UNIQUE(name, warehouse_id)',
            'La locación ya existe en este almacén.',
        ),
    ]

    @api.constrains('name', 'warehouse_id')
    def _check_unique_location_name(self):
        for record in self:
            if not record.name or not record.warehouse_id:
                continue

            # Busca si existe otra locación con el mismo nombre (sin importar mayúsculas/minúsculas) en el mismo almacén
            domain = [
                ('id', '!=', record.id),
                ('warehouse_id', '=', record.warehouse_id.id),
                ('name', '=ilike', record.name.strip()), # =ilike ignora mayúsculas/minúsculas
            ]
            existing = self.search(domain, limit=1)
            
            if existing:
                raise ValidationError(
                    _('Ya existe una locación llamada "%s" en el almacén %s.') % (
                        record.name.strip(),
                        record.warehouse_id.display_name
                    )
                )