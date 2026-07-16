from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.exceptions import ValidationError


class ComprasInventoryMove(models.Model):
    _name = 'compras.inventory.move'
    _description = 'Bitácora de Movimientos de Almacén'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'movement_date desc, id desc'

    name = fields.Char(
        string='Folio',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo'),
    )
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    destination_company_id = fields.Many2one(
        'res.company',
        string='Empresa Destino',
        default=lambda self: self.env.company,
        tracking=True,
    )
    destination_company_selector = fields.Selection(
        selection='_selection_destination_companies',
        string='Empresa Destino',
        compute='_compute_destination_company_selector',
        inverse='_inverse_destination_company_selector',
    )
    movement_date = fields.Datetime(
        string='Fecha de Movimiento',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    move_type = fields.Selection(
        [
            ('inicial', 'Inventario inicial'),
            ('entrada', 'Entrada'),
            ('salida', 'Salida'),
            ('transferencia', 'Transferencia'),
        ],
        string='Tipo de Movimiento',
        default='inicial',
        required=True,
        tracking=True,
    )
    product_id = fields.Many2one('compras.product', string='Producto', required=True, tracking=True)
    unit_id = fields.Many2one('uom.uom', string='Unidad', related='product_id.unit_id', store=True, readonly=True)
    source_warehouse_id = fields.Many2one(
        'compras.warehouse',
        string='Almacén Origen',
        default=lambda self: self._default_source_warehouse_id(),
        domain="[('company_id', '=', company_id)]",
    )
    destination_warehouse_id = fields.Many2one(
        'compras.warehouse',
        string='Almacén Destino',
        domain="[('company_id', '=', destination_company_id)]",
    )
    area_id = fields.Many2one('hr.area', string='Área', domain="[('department_id.company_id', '=', company_id)]")
    location_id = fields.Many2one(
        'compras.warehouse.location',
        string='Locación',
        domain="[('warehouse_id', '=', source_warehouse_id)]",
    )
    request_id = fields.Many2one('purchase.request', string='Solicitud de Compra', readonly=True)
    request_line_id = fields.Many2one('purchase.request.line', string='Línea de Solicitud', readonly=True)
    quantity = fields.Float(string='Cantidad', required=True, default=1.0, tracking=True)
    quantity_done = fields.Float(string='Cantidad Real', required=True, default=1.0, tracking=True)
    previous_qty = fields.Float(string='Existencia Antes', readonly=True)
    new_qty = fields.Float(string='Existencia Después', readonly=True)
    receiver_user_id = fields.Many2one('res.users', string='Recibió')
    receiver_name = fields.Char(string='Recibido por / Entregado a')
    delivered_by_id = fields.Many2one('res.users', string='Entregado por', default=lambda self: self.env.user)
    signed_by_id = fields.Many2one('res.users', string='Firma Lógica', default=lambda self: self.env.user)
    destination = fields.Char(string='Destino / Ubicación')
    status = fields.Selection(
        [
            ('completo', 'Completo'),
            ('incompleto', 'Incompleto'),
            ('defectuoso', 'Defectuoso'),
            ('faltante', 'Con Faltante'),
            ('entregado', 'Entregado'),
            ('transferido', 'Transferido'),
        ],
        string='Estado del Movimiento',
        default='entregado',
        tracking=True,
    )
    notes = fields.Text(string='Observaciones')
    registered_by_id = fields.Many2one(
        'res.users',
        string='Registrado por',
        default=lambda self: self.env.user,
        readonly=True,
    )
    registered_employee_id = fields.Many2one(
        'hr.employee',
        string='Registrado por',
        default=lambda self: self.env.user.employee_id,
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
    )
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('done', 'Confirmado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado',
        default='draft',
        tracking=True,
    )

    @api.model
    def _register_hook(self):
        result = super()._register_hook()
        env = api.Environment(self._cr, SUPERUSER_ID, {})
        move_rule = env.ref('Warehouse_Management.compras_inventory_move_company_rule', raise_if_not_found=False)
        if move_rule:
            move_rule.write({
                'domain_force': "['|', '|', ('company_id', 'in', company_ids), ('source_warehouse_id.company_id', 'in', company_ids), ('destination_warehouse_id.company_id', 'in', company_ids)]",
                'global': True,
            })
        return result

    def _default_source_warehouse_id(self):
        warehouse = self.env['compras.warehouse'].sudo().search([
            ('company_id', '=', self.env.company.id),
            ('is_main', '=', True),
        ], limit=1)
        return warehouse.id if warehouse else False

    @api.model
    def _selection_destination_companies(self):
        companies = self.env['res.company'].sudo().search([], order='name')
        return [(str(company.id), company.display_name) for company in companies]

    @api.depends('destination_company_id')
    def _compute_destination_company_selector(self):
        for rec in self:
            rec.destination_company_selector = str(rec.destination_company_id.id) if rec.destination_company_id else False

    def _inverse_destination_company_selector(self):
        company_model = self.env['res.company'].sudo()
        for rec in self:
            if rec.destination_company_selector:
                rec.destination_company_id = company_model.browse(int(rec.destination_company_selector))
            else:
                rec.destination_company_id = False

    def _get_stock_warehouse_for_move(self):
        self.ensure_one()
        if self.move_type in ('entrada', 'inicial'):
            return self.destination_warehouse_id
        if self.move_type in ('salida', 'transferencia'):
            return self.source_warehouse_id
        return False

    def _get_location_warehouse_for_move(self):
        self.ensure_one()
        return self.source_warehouse_id or (
            self.destination_warehouse_id if self.move_type == 'entrada' else False
        )

    def _get_product_qty_in_warehouse(self, product, warehouse):
        if not product or not warehouse:
            return 0.0
        inventory_line = self.env['compras.warehouse.inventory'].sudo().search([
            ('warehouse_id', '=', warehouse.id),
            ('product_id', '=', product.id),
        ], limit=1)
        return inventory_line.quantity if inventory_line else 0.0

    def _is_intercompany_transfer(self):
        self.ensure_one()
        return (
            self.move_type == 'transferencia'
            and self.destination_warehouse_id
            and self.destination_warehouse_id.company_id != self.company_id
        )

    def _prepare_destination_product_vals(self, destination_company):
        self.ensure_one()
        product = self.product_id
        return {
            'name': product.name,
            'code': product.code,
            'serial': product.serial,
            'manufacturer': product.manufacturer,
            'classification': product.classification,
            'category_id': product.category_id.id,
            'subcategory_id': product.subcategory_id.id,
            'subcategory_2': product.subcategory_2,
            'location': product.location,
            'expiration_date': product.expiration_date,
            'repair_line_id': product.repair_line_id.id,
            'company_id': destination_company.id,
            'unit_id': product.unit_id.id,
            'description': product.description,
            'brand_id': product.brand_id.id,
            'model_name': product.model_name,
            'qty_process': product.qty_process,
            'total_equipment': product.total_equipment,
            'frequency_use_days': product.frequency_use_days,
            'lead_time_days': product.lead_time_days,
            'purchase_type': product.purchase_type,
            'vendor_id': product.vendor_id.id,
            'unit_price': product.unit_price,
            'currency_id': product.currency_id.id or destination_company.currency_id.id,
            'min_qty': product.min_qty,
            'tax_ids': [(6, 0, product.tax_ids.ids)],
            'active': product.active,
        }

    def _get_or_create_destination_product(self):
        self.ensure_one()
        destination_company = self.destination_warehouse_id.company_id
        product_model = self.env['compras.product'].sudo().with_context(
            allowed_company_ids=[self.company_id.id, destination_company.id],
        )
        destination_product = product_model.search([
            ('company_id', '=', destination_company.id),
            ('code', '=', self.product_id.code),
        ], limit=1)
        if destination_product:
            return destination_product
        return product_model.create(self._prepare_destination_product_vals(destination_company))

    def _create_intercompany_destination_move(self):
        self.ensure_one()
        destination_company = self.destination_warehouse_id.company_id
        destination_product = self._get_or_create_destination_product()
        move_model = self.env['compras.inventory.move'].sudo().with_context(
            allowed_company_ids=[self.company_id.id, destination_company.id],
        )
        destination_move = move_model.create({
            'company_id': destination_company.id,
            'destination_company_id': destination_company.id,
            'movement_date': self.movement_date,
            'move_type': 'entrada',
            'product_id': destination_product.id,
            'source_warehouse_id': False,
            'destination_warehouse_id': self.destination_warehouse_id.id,
            'location_id': self.location_id.id if self.location_id and self.location_id.warehouse_id == self.destination_warehouse_id else False,
            'quantity': self.quantity,
            'quantity_done': self.quantity_done,
            'receiver_user_id': self.receiver_user_id.id,
            'receiver_name': self.receiver_name or self.delivered_by_id.name,
            'delivered_by_id': self.delivered_by_id.id,
            'signed_by_id': self.signed_by_id.id,
            'destination': self.location_id.name if self.location_id else self.destination_warehouse_id.name,
            'status': 'transferido',
            'notes': _('Entrada automática generada por transferencia interempresa desde %(source_company)s (%(folio)s).') % {
                'source_company': self.company_id.display_name,
                'folio': self.name,
            },
            'registered_employee_id': self.registered_employee_id.id or self.env.user.employee_id.id,
            'registered_by_id': self.env.user.id,
        })
        destination_move.action_confirm()

    @api.onchange('move_type')
    def _onchange_move_type(self):
        if self.move_type == 'entrada':
            self.status = 'completo'
        elif self.move_type == 'salida':
            self.status = 'entregado'
        elif self.move_type == 'transferencia':
            self.status = 'transferido'
        if self.move_type != 'transferencia' and self.company_id:
            self.destination_company_id = self.company_id

    @api.onchange('quantity')
    def _onchange_quantity(self):
        for rec in self:
            if not rec.request_line_id:
                rec.quantity_done = rec.quantity or 0.0

    @api.onchange('company_id')
    def _onchange_company_id(self):
        for rec in self:
            if rec.source_warehouse_id and rec.source_warehouse_id.company_id != rec.company_id:
                rec.source_warehouse_id = False
            if rec.area_id and rec.area_id.department_id.company_id != rec.company_id:
                rec.area_id = False
            if rec.move_type != 'transferencia' or not rec.destination_company_id:
                rec.destination_company_id = rec.company_id

    @api.onchange('destination_company_selector')
    def _onchange_destination_company_selector(self):
        company_model = self.env['res.company'].sudo()
        for rec in self:
            rec.destination_company_id = (
                company_model.browse(int(rec.destination_company_selector))
                if rec.destination_company_selector else False
            )

    @api.onchange('destination_company_id')
    def _onchange_destination_company_id(self):
        for rec in self:
            if rec.destination_warehouse_id and rec.destination_warehouse_id.company_id != rec.destination_company_id:
                rec.destination_warehouse_id = False

    @api.onchange('move_type', 'product_id', 'source_warehouse_id', 'destination_warehouse_id', 'quantity', 'quantity_done')
    def _onchange_move_preview_quantities(self):
        for rec in self:
            warehouse = rec._get_stock_warehouse_for_move()
            moved_qty = rec.quantity_done or rec.quantity or 0.0
            if not rec.product_id or not warehouse:
                rec.previous_qty = 0.0
                rec.new_qty = 0.0
                continue

            previous_qty = rec._get_product_qty_in_warehouse(rec.product_id, warehouse)
            if rec.move_type in ('entrada', 'inicial'):
                rec.new_qty = previous_qty + moved_qty
            elif rec.move_type in ('salida', 'transferencia'):
                rec.new_qty = previous_qty - moved_qty
            else:
                rec.new_qty = previous_qty
            rec.previous_qty = previous_qty

    @api.onchange('move_type', 'company_id', 'source_warehouse_id', 'destination_company_id', 'destination_warehouse_id')
    def _onchange_destination_warehouse_id(self):
        area_domain_by_record = [('id', '=', False)]
        location_domain_by_record = [('id', '=', False)]
        destination_warehouse_domain_by_record = [('id', '=', False)]
        for rec in self:
            area_company = rec.company_id
            area_domain = [('id', '=', False)]
            location_domain = [('id', '=', False)]
            destination_warehouse_domain = [('id', '=', False)]
            if area_company:
                area_domain = [('department_id.company_id', '=', area_company.id)]

            if rec.destination_company_id:
                destination_warehouse_domain = [('company_id', '=', rec.destination_company_id.id)]

            location_warehouse = rec.source_warehouse_id
            if location_warehouse:
                location_domain = [('warehouse_id', '=', location_warehouse.id)]

            area_domain_by_record = area_domain
            location_domain_by_record = location_domain
            destination_warehouse_domain_by_record = destination_warehouse_domain

            if rec.destination_warehouse_id and not rec.destination_company_id:
                rec.destination_company_id = rec.destination_warehouse_id.company_id
            if rec.area_id and rec.area_id.department_id.company_id != area_company:
                rec.area_id = False
            if rec.location_id and rec.location_id.warehouse_id != location_warehouse:
                rec.location_id = False
            if rec.destination_warehouse_id and rec.destination_warehouse_id.company_id != rec.destination_company_id:
                rec.destination_warehouse_id = False

        return {
            'domain': {
                'area_id': area_domain_by_record,
                'location_id': location_domain_by_record,
                'destination_warehouse_id': destination_warehouse_domain_by_record,
            }
        }

    @api.constrains('company_id', 'destination_company_id', 'destination_warehouse_id', 'area_id', 'location_id')
    def _check_destination_consistency(self):
        for rec in self:
            location_warehouse = rec._get_location_warehouse_for_move()
            if rec.area_id and rec.area_id.department_id.company_id != rec.company_id:
                raise ValidationError(_('El área debe pertenecer a la empresa seleccionada.'))
            if rec.location_id and not location_warehouse:
                raise ValidationError(_('Debes seleccionar un almacén antes de elegir una locación.'))
            if rec.location_id and location_warehouse and rec.location_id.warehouse_id != location_warehouse:
                raise ValidationError(_('La locación debe pertenecer al almacén correspondiente al movimiento.'))
            if (
                rec.destination_warehouse_id
                and rec.destination_company_id
                and rec.destination_warehouse_id.company_id != rec.destination_company_id
            ):
                raise ValidationError(_('El almacén destino debe pertenecer a la empresa destino seleccionada.'))

    @api.constrains('quantity', 'quantity_done')
    def _check_quantities(self):
        for rec in self:
            if rec.quantity <= 0 or rec.quantity_done <= 0:
                raise ValidationError(_('Las cantidades deben ser mayores a cero.'))
            if rec.request_line_id and rec.quantity_done > rec.quantity:
                raise ValidationError(_('La cantidad real no puede ser mayor a la cantidad esperada.'))
 
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('compras.inventory.move') or _('Nuevo')
            if not vals.get('request_line_id') and vals.get('quantity') and not vals.get('quantity_done'):
                vals['quantity_done'] = vals['quantity']
        return super().create(vals_list)

    def write(self, vals):
        if 'quantity' in vals and 'quantity_done' not in vals:
            manual_moves = self.filtered(lambda rec: not rec.request_line_id)
            if manual_moves:
                vals = dict(vals, quantity_done=vals['quantity'])
        return super().write(vals)
    
    @api.onchange('move_type', 'company_id', 'source_warehouse_id')
    def _onchange_initial_inventory_sync(self):
        """
        Si el tipo de movimiento es inventario inicial, copiamos automaticamente la empresa y almacen de origen hacia los campos de destino.
        """
        for rec in self:
            # Copiamos empresa origen a empresa destino
            if rec.move_type == 'inicial':
                if rec.company_id:
                    rec.destination_company_id = rec.company_id
                    rec.destination_company_selector = str(rec.company_id.id)

            #Copiamos almacen origen a almacen destino
            if rec.source_warehouse_id:
                rec.destination_warehouse_id = rec.source_warehouse_id

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.move_type == 'inicial':
                # En inventario inicial, origen y destino deben quedar alineados.
                if rec.company_id and not rec.destination_company_id:
                    rec.destination_company_id = rec.company_id
                if rec.source_warehouse_id and not rec.destination_warehouse_id:
                    rec.destination_warehouse_id = rec.source_warehouse_id
                elif rec.destination_warehouse_id and not rec.source_warehouse_id:
                    rec.source_warehouse_id = rec.destination_warehouse_id
            stock_warehouse = rec._get_stock_warehouse_for_move()
            if rec.move_type in ('entrada', 'inicial') and not rec.destination_warehouse_id:
                raise ValidationError(_('Debes indicar el almacén destino para una entrada.'))
            if rec.move_type in ('salida', 'transferencia') and not rec.source_warehouse_id:
                raise ValidationError(_('Debes indicar el almacén origen para este movimiento.'))

            previous_qty = rec._get_product_qty_in_warehouse(rec.product_id, stock_warehouse)
            moved_qty = rec.quantity_done or rec.quantity
            is_intercompany_transfer = rec._is_intercompany_transfer()
            if rec.move_type == 'salida' and moved_qty > previous_qty:
                raise ValidationError(_('No hay suficiente existencia para dar salida a este producto.'))
            if is_intercompany_transfer and moved_qty > previous_qty:
                raise ValidationError(_('No hay suficiente existencia para transferir este producto a otra empresa.'))
            if rec.move_type == 'transferencia' and not rec.destination_warehouse_id:
                raise ValidationError(_('Debes indicar el almacén destino para una transferencia.'))
            if rec.move_type == 'salida' and not (rec.area_id or rec.location_id):
                raise ValidationError(_('Debes indicar un área o locación para la salida del producto.'))

            if rec.location_id and not rec.destination:
                rec.destination = rec.location_id.name

            if rec.move_type in ('entrada', 'inicial'):
                new_qty = previous_qty + moved_qty
            elif rec.move_type == 'salida':
                new_qty = previous_qty - moved_qty
            elif is_intercompany_transfer:
                new_qty = previous_qty - moved_qty
            else:
                new_qty = previous_qty

            rec.write({
                'previous_qty': previous_qty,
                'new_qty': new_qty,
                'state': 'done',
            })

            if is_intercompany_transfer:
                rec._create_intercompany_destination_move()

    def action_cancel(self):
        self.write({'state': 'cancelled'})
