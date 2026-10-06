# -*- coding: utf-8 -*-

from odoo import api, fields, models


class CustomerServiceCliente(models.Model):
    _name = 'customer_service.cliente'
    _description = 'Cliente'
    _order = 'name'

    name = fields.Char(string='Cliente', required=True)
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Observaciones')
    pedido_ids = fields.One2many('pedidos.pedidos', 'cliente_id', string='Pedidos')
    pedido_count = fields.Integer(string='Pedidos', compute='_compute_pedido_count')

    def _compute_pedido_count(self):
        data = self.env['pedidos.pedidos']._read_group(
            [('cliente_id', 'in', self.ids)], ['cliente_id'], ['__count'])
        counts = {cliente.id: count for cliente, count in data}
        for rec in self:
            rec.pedido_count = counts.get(rec.id, 0)

    def action_view_pedidos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pedidos',
            'res_model': 'pedidos.pedidos',
            'view_mode': 'list,form',
            'domain': [('cliente_id', '=', self.id)],
            'context': {'default_cliente_id': self.id},
        }

class PedidosLine(models.Model):
    _name = 'pedidos.line'
    _description = 'Request Line del Pedido'
    _order = 'id'

    pedido_id = fields.Many2one('pedidos.pedidos', string='WON', required=True, ondelete='cascade', index=True)
    cantidad_tarimas = fields.Float(string='Cantidad de tarimas', digits=(16, 2))
    tipo_empaque = fields.Selection([
        ('bags', 'Bags'),
        ('cases', 'Cases'),
        ('cups', 'Cups'),
        ('drums', 'Drums'),
        ('mix', 'Mix'),
        ('pails', 'Pails'),
        ('totes', 'Totes'),
        ('tubs', 'Tubs'),
    ], string='Tipo de empaque')
    cantidad_libras = fields.Float(string='Cantidad de libras', digits=(16, 2))
    unidad = fields.Selection([
        ('libras', 'Libras'),
        ('kilogramos', 'Kilogramos'),
        ('litros', 'Litros'),
        # ('mts', 'Mts'), no se sabe que es est unidad en caso de necesitarla despues descomentar esta linea.
        ('onzas', 'Onzas'),
        ('piezas', 'Piezas'),
    ], string='Unidad')
    clave = fields.Char(string='Clave')
    product_id = fields.Many2one(
        'compras.product',
        string='Descripción',
        domain=[('is_production', '=', True)],
        context={'default_is_production': True},
    )
    precio = fields.Float(
        string='Precio',
        digits=(16, 2),
        compute='_compute_precio',
        store=True,
        readonly=False,
    )
    divisa = fields.Selection([('usd', 'USD'), ('mxn', 'MXN')], string='Divisa')
    flete_inc = fields.Boolean(string='Flete Inc')

    @api.depends('product_id')
    def _compute_precio(self):
        for line in self:
            line.precio = line.product_id.unit_price or 0.0
