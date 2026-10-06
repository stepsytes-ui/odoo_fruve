# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Pedidos(models.Model):
    _name = 'pedidos.pedidos'
    _description = 'Pedidos (Work Order)'
    _order = 'id desc'
    _rec_name = 'won'

    won = fields.Char(string='WON', readonly=True, copy=False, default='/', index=True)
    planta_asignada = fields.Reference(
        selection=[('res.company', 'Empresa'), ('compras.warehouse', 'Almacén')],
        string='Planta asignada',
    )
    sample = fields.Boolean(string='Sample')
    master = fields.Boolean(string='Master')
    maquila = fields.Selection([('si', 'Sí'), ('no', 'No')], string='Maquila', default='no')
    cliente_id = fields.Many2one('customer_service.cliente', string='Cliente', index=True)
    po = fields.Char(string='PO')
    fecha_entrega = fields.Date(string='Fecha entrega')
    line_ids = fields.One2many('pedidos.line', 'pedido_id', string='Request Line')
    notas = fields.Text(string='Notas')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('won') or vals['won'] == '/':
                vals['won'] = self.env['ir.sequence'].next_by_code('pedidos.pedidos.won') or '/'
        return super().create(vals_list)
