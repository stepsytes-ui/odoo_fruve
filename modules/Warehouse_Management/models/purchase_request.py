from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.sql import column_exists


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _description = 'Solicitud de Compra'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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
    create_date = fields.Datetime(string='Fecha Creación', readonly=True)
    department_id = fields.Many2one(
        'hr.department',
        string='Departamento',
        domain="[('company_id', '=', company_id)]",
    )
    solicitante_id = fields.Many2one(
        'hr.employee',
        string='Solicitante',
        required=True,
        default=lambda self: self.env.user.employee_id,
        domain=lambda self: self._get_solicitante_domain(),
    )

    def _get_solicitante_domain(self):
        return [
            ('company_id', '=', self.env.company.id),
            ('active', '=', True),
        ]
    supervisor_id = fields.Many2one(
        'res.users',
        string='Supervisor de Área',
        domain=lambda self: self._get_supervisor_domain(),
    )
    authorizer_id = fields.Many2one(
        'hr.employee',
        string='Autoriza',
        domain=lambda self: self._get_authorizer_domain(),
    )

    def _get_supervisor_domain(self):
        group = self.env.ref('overtime.group_overtime_supervisor', raise_if_not_found=False)
        if group:
            return [('groups_id', 'in', [group.id])]
        return []

    def _get_authorizer_domain(self):
        return [
            ('company_id', '=', self.env.company.id),
            ('active', '=', True),
        ]
    comments = fields.Text(string='Comentarios')
    payment_type = fields.Selection(
        [
            ('contado', 'Contado'),
            ('credito', 'Crédito'),
        ],
        string='Tipo de Pago',
        required=True,
        default='contado',
    )
    currency_type = fields.Selection(
        [
            ('mxn', 'Pesos (MXN)'),
            ('usd', 'Dólares (USD)'),
        ],
        string='Moneda',
        required=True,
        default='mxn',
    )
    line_ids = fields.One2many(
        'purchase.request.line',
        'request_id',
        string='Productos / Servicios',
    )
    warehouse_id = fields.Many2one(
        'compras.warehouse',
        string='Almacén de Recepción',
        required=True,
        default=lambda self: self._default_warehouse_id(),
    )
    movement_ids = fields.One2many(
        'compras.inventory.move',
        'request_id',
        string='Bitácora de Movimientos',
    )
    total_amount = fields.Float(
        string='Total',
        compute='_compute_total_amount',
        store=True,
        digits=(16, 2),
    )
    state = fields.Selection(
        [
            ('activa', 'Activa'),
            ('inactiva', 'Inactiva'),
            ('autorizada', 'Autorizada'),
            ('recibida', 'Recibida'),
        ],
        string='Estado',
        default='activa',
        required=True,
        tracking=True,
    )
    rejection_reason = fields.Text(string='Motivo de Rechazo', readonly=True)
    rejected_by_id = fields.Many2one('res.users', string='Rechazado por', readonly=True)
    approved_by_id = fields.Many2one('res.users', string='Aprobado por', readonly=True)
    received_by_id = fields.Many2one('res.users', string='Recibido por', readonly=True)

    def _default_warehouse_id(self):
        warehouse_model = self.env['compras.warehouse'].sudo()
        warehouse = warehouse_model.search([
            ('company_id', '=', self.env.company.id),
            ('is_main', '=', True),
        ], limit=1)
        if not warehouse:
            warehouse = warehouse_model.create({
                'name': 'Almacén Principal',
                'code': 'MAIN',
                'company_id': self.env.company.id,
                'is_main': True,
            })
        return warehouse.id

    @api.depends('line_ids.subtotal')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.line_ids.mapped('subtotal'))

    def _prepare_product_vals_from_line(self, line):
        legacy_tmpl = line.product_id.product_tmpl_id if line.product_id else False
        vendor = line.vendor_id or (legacy_tmpl.seller_ids[:1].partner_id if legacy_tmpl and legacy_tmpl.seller_ids else False)
        taxes = line.tax_ids.ids or (legacy_tmpl.taxes_id.ids if legacy_tmpl else [])
        unit = line.unit_id or (legacy_tmpl.uom_id if legacy_tmpl else False)
        return {
            'name': line.description or (legacy_tmpl.name if legacy_tmpl else _('Producto sin nombre')),
            'company_id': self.company_id.id,
            'unit_id': unit.id if unit else False,
            'description': line.description or (legacy_tmpl.description_purchase if legacy_tmpl else ''),
            'brand_id': line.brand_id.id if line.brand_id else False,
            'model_name': line.model_name or '',
            'vendor_id': vendor.id if vendor else False,
            'unit_price': line.unit_price or (legacy_tmpl.list_price if legacy_tmpl else 0.0),
            'tax_ids': [(6, 0, taxes)],
        }

    def _get_or_create_product_from_line(self, line):
        if line.warehouse_product_id:
            return line.warehouse_product_id
        product = self.env['compras.product'].create(self._prepare_product_vals_from_line(line))
        line.warehouse_product_id = product.id
        return product

    def _auto_init(self):
        # Migrate old values of authorizer_id from res.users ids to hr.employee ids.
        if column_exists(self.env.cr, self._table, 'authorizer_id'):
            self.env.cr.execute("""
                UPDATE purchase_request pr
                   SET authorizer_id = he.id
                  FROM hr_employee he
                 WHERE pr.authorizer_id IS NOT NULL
                   AND he.user_id = pr.authorizer_id
            """)
            self.env.cr.execute("""
                UPDATE purchase_request pr
                   SET authorizer_id = NULL
                 WHERE pr.authorizer_id IS NOT NULL
                   AND NOT EXISTS (
                       SELECT 1
                         FROM hr_employee he
                        WHERE he.id = pr.authorizer_id
                   )
            """)
        return super()._auto_init()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('purchase.request') or _('Nuevo')
                )
        return super().create(vals_list)

    def action_approve(self):
        self.ensure_one()
        if self.state != 'activa':
            raise ValidationError(_('Solo se pueden aprobar solicitudes en estado Activa.'))
        if not self.line_ids:
            raise ValidationError(_('Debes agregar al menos un producto o servicio a la solicitud.'))

        for line in self.line_ids:
            self._get_or_create_product_from_line(line)

        self.write({
            'state': 'autorizada',
            'approved_by_id': self.env.user.id,
        })

    def action_reject(self):
        self.ensure_one()
        if self.state != 'activa':
            raise ValidationError(_('Solo se pueden rechazar solicitudes en estado Activa.'))
        return {
            'name': _('Motivo de Rechazo'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_receive(self):
        self.ensure_one()
        if self.state != 'autorizada':
            raise ValidationError(_('Solo se pueden marcar como recibidas las solicitudes Autorizadas.'))
        return {
            'name': _('Checklist de Recepción'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.receipt.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
            },
        }

    def action_cancel_for_edit(self):
        for request in self:
            if request.state not in ('autorizada', 'recibida'):
                raise ValidationError(_('Solo se pueden cancelar para edición solicitudes Autorizadas o Recibidas.'))

            if not (
                self.env.user.has_group('Warehouse_Management.group_compras_usuario')
                or self.env.user.has_group('Warehouse_Management.group_compras_encargado')
            ):
                raise AccessError(_('No tienes permisos para cancelar la solicitud para edición.'))

            # Si ya se recibió, anula los movimientos de entrada para recalcular existencia.
            if request.state == 'recibida':
                done_moves = request.movement_ids.filtered(lambda move: move.state == 'done')
                if done_moves:
                    done_moves.action_cancel()

            request.write({
                'state': 'activa',
                'received_by_id': False,
                'approved_by_id': False,
            })

    def action_process_receipt_from_checklist(self, receiver_user=False, warehouse=False, location=False):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_('No hay líneas para recibir en esta solicitud.'))

        receiver = receiver_user or self.env.user
        warehouse = warehouse or self.warehouse_id
        if location and location.warehouse_id != warehouse:
            raise ValidationError(_('La locación seleccionada no pertenece al almacén de recepción.'))

        for line in self.line_ids:
            product = self._get_or_create_product_from_line(line)
            received_qty = line.received_qty or 0
            if received_qty > line.quantity:
                raise ValidationError(_('La cantidad recibida no puede ser mayor a la solicitada.'))

            move_status = line.receipt_status or 'completo'
            previous_qty = product.qty_on_hand
            self.env['compras.inventory.move'].create({
                'company_id': self.company_id.id,
                'destination_company_id': warehouse.company_id.id if warehouse else self.company_id.id,
                'movement_date': fields.Datetime.now(),
                'move_type': 'entrada',
                'product_id': product.id,
                'destination_warehouse_id': warehouse.id if warehouse else False,
                'location_id': location.id if location else False,
                'request_id': self.id,
                'request_line_id': line.id,
                'quantity': line.quantity,
                'quantity_done': received_qty,
                'previous_qty': previous_qty,
                'new_qty': previous_qty + received_qty,
                'receiver_user_id': receiver.id,
                'receiver_name': receiver.name,
                'delivered_by_id': self.env.user.id,
                'signed_by_id': self.env.user.id,
                'destination': location.name if location else (warehouse.name if warehouse else 'Almacén Principal'),
                'status': move_status,
                'notes': line.receipt_notes or self.comments or '',
                'registered_employee_id': self.env.user.employee_id.id,
                'registered_by_id': self.env.user.id,
                'state': 'done',
            })

        self.write({
            'state': 'recibida',
            'received_by_id': receiver.id,
            'warehouse_id': warehouse.id if warehouse else self.warehouse_id.id,
        })

    def _is_warehouse_only_user(self):
        user = self.env.user
        return (
            user.has_group('Warehouse_Management.group_compras_almacenista')
            and not user.has_group('Warehouse_Management.group_compras_encargado')
        )

    def _check_warehouse_user_can_edit(self):
        if not self._is_warehouse_only_user():
            return
        locked_requests = self.filtered(lambda request: request.state == 'recibida')
        if locked_requests:
            raise AccessError(_('Los usuarios de almacén no pueden editar solicitudes de compra recibidas.'))

    def write(self, vals):
        self._check_warehouse_user_can_edit()
        return super().write(vals)

    def unlink(self):
        self._check_warehouse_user_can_edit()
        return super().unlink()
