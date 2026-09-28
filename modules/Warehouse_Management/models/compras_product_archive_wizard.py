from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ComprasProductArchiveWizard(models.TransientModel):
    _name = 'compras.product.archive.wizard'
    _description = 'Confirmación para eliminar producto del consolidado'

    product_id = fields.Many2one('compras.product', string='Producto', required=True, readonly=True)
    total_stock = fields.Float(string='Existencia total que se dará de baja', compute='_compute_stock_summary', readonly=True)
    stock_summary = fields.Text(string='Existencias por almacén', compute='_compute_stock_summary', readonly=True)
    deletion_context = fields.Text(string='Contexto de la eliminación')
    confirm_deletion = fields.Boolean(string='Confirmo que deseo eliminar y dar de baja estas existencias')

    @api.depends('product_id')
    def _compute_stock_summary(self):
        inventory_model = self.env['compras.warehouse.inventory'].sudo()
        for wizard in self:
            lines = inventory_model.search([
                ('product_id', '=', wizard.product_id.id),
                ('quantity', '>', 0),
            ], order='company_id, warehouse_id') if wizard.product_id else inventory_model
            wizard.total_stock = sum(lines.mapped('quantity'))
            wizard.stock_summary = '\n'.join(
                _('%(company)s / %(warehouse)s: %(quantity)s') % {
                    'company': line.company_id.display_name,
                    'warehouse': line.warehouse_id.display_name,
                    'quantity': line.quantity,
                }
                for line in lines
            ) or _('No hay existencias positivas registradas.')

    def action_confirm_deletion(self):
        self.ensure_one()
        if not self.env.user.has_group('Warehouse_Management.group_compras_encargado'):
            raise UserError(_('Solo un encargado de compras puede eliminar productos del consolidado.'))
        if not self.confirm_deletion:
            raise ValidationError(_('Debes confirmar que comprendes las consecuencias de esta acción.'))

        product = self.product_id
        inventory_model = self.env['compras.warehouse.inventory'].sudo()
        lines = inventory_model.search([
            ('product_id', '=', product.id),
            ('quantity', '>', 0),
        ], order='company_id, warehouse_id')
        inaccessible_company_lines = lines.filtered(lambda line: line.company_id not in self.env.companies)
        if inaccessible_company_lines:
            raise UserError(_(
                'Activa todas las empresas con existencias de este producto antes de eliminarlo del consolidado.'
            ))

        notes = _('Contexto: %s') % self.deletion_context.strip() if self.deletion_context and self.deletion_context.strip() else False

        move_model = self.env['compras.inventory.move']
        if not lines:
            move = move_model.create({
                'company_id': product.company_id.id,
                'move_type': 'eliminacion',
                'product_id': product.id,
                'source_warehouse_id': product.inventory_warehouse_id.id,
                'quantity': 0.0,
                'quantity_done': 0.0,
                'receiver_name': self.env.user.name,
                'destination': _('Baja del consolidado'),
                'status': 'entregado',
                'notes': notes,
                'registered_by_id': self.env.user.id,
                'delivered_by_id': self.env.user.id,
            })
            move.action_confirm()
        else:
            for line in lines:
                move = move_model.create({
                    'company_id': line.company_id.id,
                    'move_type': 'eliminacion',
                    'product_id': product.id,
                    'source_warehouse_id': line.warehouse_id.id,
                    'quantity': line.quantity,
                    'quantity_done': line.quantity,
                    'receiver_name': self.env.user.name,
                    'destination': _('Baja del consolidado'),
                    'status': 'entregado',
                    'notes': notes,
                    'registered_by_id': self.env.user.id,
                    'delivered_by_id': self.env.user.id,
                })
                move.action_confirm()

        product.write({'active': False})
        action = self.env.ref('Warehouse_Management.compras_product_action').read()[0]
        action.update({
            'view_mode': 'list',
            'views': [(self.env.ref('Warehouse_Management.compras_product_view_list').id, 'list')],
            'view_id': self.env.ref('Warehouse_Management.compras_product_view_list').id,
            'target': 'current',
        })
        return action