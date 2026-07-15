from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.osv import expression


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
    location_ids = fields.One2many(
        'compras.warehouse.location',
        'warehouse_id',
        string='Locaciones',
    )
    movement_count = fields.Integer(string='Movimientos', compute='_compute_movement_count')
    inventory_line_count = fields.Integer(string='Productos en Inventario', compute='_compute_inventory_line_count')

    @api.depends('source_move_ids', 'destination_move_ids')
    def _compute_movement_count(self):
        for warehouse in self:
            warehouse.movement_count = len(warehouse.source_move_ids | warehouse.destination_move_ids)

    def _compute_inventory_line_count(self):
        inventory_model = self.env['compras.warehouse.inventory']
        grouped = inventory_model.read_group(
            [('warehouse_id', 'in', self.ids)],
            ['warehouse_id'],
            ['warehouse_id'],
        )
        grouped_map = {item['warehouse_id'][0]: item['warehouse_id_count'] for item in grouped if item.get('warehouse_id')}
        for warehouse in self:
            warehouse.inventory_line_count = grouped_map.get(warehouse.id, 0)

    def action_open_inventory(self):
        self.ensure_one()
        action = self.env.ref('Warehouse_Management.compras_warehouse_inventory_action').read()[0]
        action['domain'] = [('warehouse_id', '=', self.id)]
        action['context'] = dict(self.env.context, default_warehouse_id=self.id)
        return action

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not self.env.context.get('allow_cross_company_destination_warehouse'):
            return super().name_search(name=name, args=args, operator=operator, limit=limit)

        args = args or []
        if name:
            search_domain = expression.AND([
                args,
                ['|', ('name', operator, name), ('code', operator, name)],
            ])
        else:
            search_domain = args

        warehouses = self.sudo().search(search_domain, limit=limit)
        return [(warehouse.id, warehouse.display_name) for warehouse in warehouses]

    _sql_constraints = [
        ('code_company_unique', 'unique(code, company_id)', 'El código del almacén debe ser único por empresa.'),
    ]

    @api.model
    def _register_hook(self):
        result = super()._register_hook()
        env = api.Environment(self._cr, SUPERUSER_ID, {})

        warehouse_model = env.ref('Warehouse_Management.model_compras_warehouse', raise_if_not_found=False)
        if not warehouse_model:
            return result

        global_rule = env.ref('Warehouse_Management.compras_warehouse_company_rule', raise_if_not_found=False)
        if global_rule:
            global_rule.write({
                'domain_force': "[(1, '=', 1)]",
                'global': True,
                'groups': [(5, 0, 0)],
            })

        user_group = env.ref('Warehouse_Management.group_compras_usuario', raise_if_not_found=False)
        if user_group:
            user_rule = env.ref('Warehouse_Management.compras_warehouse_company_rule_usuario', raise_if_not_found=False)
            user_rule_vals = {
                'name': 'Compras Warehouse User Company Rule',
                'model_id': warehouse_model.id,
                'domain_force': "[('company_id', 'in', company_ids)]",
                'global': False,
                'groups': [(6, 0, [user_group.id])],
            }
            if user_rule:
                user_rule.write(user_rule_vals)
            else:
                env['ir.rule'].create(user_rule_vals)

        return result
