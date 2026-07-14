from odoo import _, fields, models, tools
from odoo.exceptions import ValidationError


class ComprasWarehouseInventory(models.Model):
    _name = 'compras.warehouse.inventory'
    _description = 'Inventario por Almacén'
    _auto = False
    _order = 'warehouse_id, product_name'

    warehouse_id = fields.Many2one('compras.warehouse', string='Almacén', readonly=True)
    company_id = fields.Many2one('res.company', string='Empresa', readonly=True)
    product_id = fields.Many2one('compras.product', string='Producto', readonly=True)
    product_db_id = fields.Integer(string='ID Producto', readonly=True)
    product_name = fields.Char(string='Nombre del producto', readonly=True)
    product_description = fields.Text(string='Descripción de producto', readonly=True)
    quantity = fields.Float(string='Cantidad', readonly=True)
    location = fields.Char(string='Locación', readonly=True)

    def action_remove_selected_inventory(self):
        move_model = self.env['compras.inventory.move']
        removed_count = 0

        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_(
                    'El producto %(product)s no tiene cantidad positiva para eliminar en el almacén %(warehouse)s.'
                ) % {
                    'product': line.product_name,
                    'warehouse': line.warehouse_id.display_name,
                })

            move = move_model.create({
                'company_id': line.company_id.id,
                'move_type': 'salida',
                'product_id': line.product_id.id,
                'source_warehouse_id': line.warehouse_id.id,
                'quantity': line.quantity,
                'quantity_done': line.quantity,
                'receiver_name': self.env.user.name,
                'destination': _('Eliminación manual desde inventario'),
                'status': 'entregado',
                'notes': _('Salida generada desde la acción "Eliminar del inventario".'),
            })
            move.action_confirm()
            removed_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Inventario actualizado'),
                'message': _('%(count)s producto(s) fueron eliminados del inventario seleccionado.') % {
                    'count': removed_count,
                },
                'type': 'success',
                'sticky': False,
            },
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW compras_warehouse_inventory AS (
                WITH move_lines AS (
                    SELECT
                        move.destination_warehouse_id AS warehouse_id,
                        move.product_id AS product_id,
                        move.quantity_done AS qty_delta
                    FROM compras_inventory_move move
                    WHERE move.state = 'done'
                      AND move.move_type = 'entrada'
                      AND move.destination_warehouse_id IS NOT NULL

                    UNION ALL

                    SELECT
                        move.source_warehouse_id AS warehouse_id,
                        move.product_id AS product_id,
                        -move.quantity_done AS qty_delta
                    FROM compras_inventory_move move
                    WHERE move.state = 'done'
                      AND move.move_type = 'salida'
                      AND move.source_warehouse_id IS NOT NULL

                    UNION ALL

                    SELECT
                        move.source_warehouse_id AS warehouse_id,
                        move.product_id AS product_id,
                        -move.quantity_done AS qty_delta
                    FROM compras_inventory_move move
                    WHERE move.state = 'done'
                      AND move.move_type = 'transferencia'
                      AND move.source_warehouse_id IS NOT NULL

                    UNION ALL

                    SELECT
                        move.destination_warehouse_id AS warehouse_id,
                        move.product_id AS product_id,
                        move.quantity_done AS qty_delta
                    FROM compras_inventory_move move
                    JOIN compras_warehouse destination_warehouse
                        ON destination_warehouse.id = move.destination_warehouse_id
                    WHERE move.state = 'done'
                      AND move.move_type = 'transferencia'
                      AND move.destination_warehouse_id IS NOT NULL
                      AND destination_warehouse.company_id = move.company_id
                ),
                stock_lines AS (
                    SELECT
                        move_lines.warehouse_id AS warehouse_id,
                        move_lines.product_id AS product_id,
                        SUM(move_lines.qty_delta) AS quantity
                    FROM move_lines
                    GROUP BY move_lines.warehouse_id, move_lines.product_id
                    HAVING SUM(move_lines.qty_delta) <> 0
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY stock_lines.warehouse_id, product.name, product.id) AS id,
                    stock_lines.warehouse_id AS warehouse_id,
                    warehouse.company_id AS company_id,
                    stock_lines.product_id AS product_id,
                    product.id AS product_db_id,
                    product.name AS product_name,
                    product.description AS product_description,
                    stock_lines.quantity AS quantity,
                    COALESCE(last_location.location_name, product.location) AS location
                FROM stock_lines
                JOIN compras_warehouse warehouse ON warehouse.id = stock_lines.warehouse_id
                JOIN compras_product product ON product.id = stock_lines.product_id
                LEFT JOIN LATERAL (
                    SELECT
                        warehouse_location.name AS location_name
                    FROM compras_inventory_move move
                    LEFT JOIN compras_warehouse destination_warehouse
                        ON destination_warehouse.id = move.destination_warehouse_id
                    JOIN compras_warehouse_location warehouse_location
                        ON warehouse_location.id = move.location_id
                    WHERE move.state = 'done'
                      AND move.product_id = stock_lines.product_id
                      AND move.location_id IS NOT NULL
                      AND (
                            (move.move_type = 'entrada' AND move.destination_warehouse_id = stock_lines.warehouse_id)
                         OR (move.move_type = 'salida' AND move.source_warehouse_id = stock_lines.warehouse_id)
                         OR (move.move_type = 'transferencia' AND move.source_warehouse_id = stock_lines.warehouse_id)
                         OR (
                                move.move_type = 'transferencia'
                            AND move.destination_warehouse_id = stock_lines.warehouse_id
                            AND destination_warehouse.company_id = move.company_id
                         )
                      )
                    ORDER BY move.movement_date DESC, move.id DESC
                    LIMIT 1
                ) AS last_location ON TRUE
            )
        """)