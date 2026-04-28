from odoo import api, fields, models, _
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
    movement_date = fields.Datetime(
        string='Fecha de Movimiento',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    move_type = fields.Selection(
        [
            ('entrada', 'Entrada'),
            ('salida', 'Salida'),
            ('transferencia', 'Transferencia'),
        ],
        string='Tipo de Movimiento',
        default='salida',
        required=True,
        tracking=True,
    )
    product_id = fields.Many2one('compras.product', string='Producto', required=True, tracking=True)
    unit_id = fields.Many2one('uom.uom', string='Unidad', related='product_id.unit_id', store=True, readonly=True)
    source_warehouse_id = fields.Many2one('compras.warehouse', string='Almacén Origen', default=lambda self: self._default_source_warehouse_id())
    destination_warehouse_id = fields.Many2one('compras.warehouse', string='Almacén Destino')
    area_id = fields.Many2one('hr.area', string='Área Destino')
    request_id = fields.Many2one('purchase.request', string='Solicitud de Compra', readonly=True)
    request_line_id = fields.Many2one('purchase.request.line', string='Línea de Solicitud', readonly=True)
    quantity = fields.Float(string='Cantidad Esperada', required=True, default=1.0)
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

    def _default_source_warehouse_id(self):
        warehouse = self.env['compras.warehouse'].sudo().search([
            ('company_id', '=', self.env.company.id),
            ('is_main', '=', True),
        ], limit=1)
        return warehouse.id if warehouse else False

    @api.onchange('move_type')
    def _onchange_move_type(self):
        if self.move_type == 'entrada':
            self.status = 'completo'
        elif self.move_type == 'salida':
            self.status = 'entregado'
        elif self.move_type == 'transferencia':
            self.status = 'transferido'

    @api.constrains('quantity', 'quantity_done')
    def _check_quantities(self):
        for rec in self:
            if rec.quantity <= 0 or rec.quantity_done <= 0:
                raise ValidationError(_('Las cantidades deben ser mayores a cero.'))
            if rec.quantity_done > rec.quantity:
                raise ValidationError(_('La cantidad real no puede ser mayor a la cantidad esperada.'))
 
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('compras.inventory.move') or _('Nuevo')
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            previous_qty = rec.product_id.qty_on_hand
            moved_qty = rec.quantity_done or rec.quantity
            if rec.move_type == 'salida' and moved_qty > previous_qty:
                raise ValidationError(_('No hay suficiente existencia para dar salida a este producto.'))
            if rec.move_type == 'transferencia' and not rec.destination_warehouse_id:
                raise ValidationError(_('Debes indicar el almacén destino para una transferencia.'))
            if rec.move_type == 'salida' and not (rec.area_id or rec.destination or rec.receiver_user_id or rec.receiver_name):
                raise ValidationError(_('Debes indicar a qué área o persona se entregó el producto.'))

            if rec.move_type == 'entrada':
                new_qty = previous_qty + moved_qty
            elif rec.move_type == 'salida':
                new_qty = previous_qty - moved_qty
            else:
                new_qty = previous_qty

            rec.write({
                'previous_qty': previous_qty,
                'new_qty': new_qty,
                'state': 'done',
            })

    def action_cancel(self):
        self.write({'state': 'cancelled'})
