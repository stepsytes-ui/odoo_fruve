from lxml import etree

from odoo import api, models


class WarehouseReadonlyViews(models.AbstractModel):
    _inherit = 'base'

    @api.model
    @api.readonly
    def get_views(self, views, options=None):
        result = super().get_views(views, options=options)
        if not self.env.user.has_group('Warehouse_Management.group_almacen_solo_visualizacion'):
            return result

        warehouse_models = {
            'compras.product', 'compras.product.category', 'compras.product.subcategory',
            'compras.repair.line', 'compras.equipment.number', 'compras.process.product',
            'compras.packaging.material', 'compras.inventory.move', 'compras.move.type',
            'compras.warehouse', 'compras.warehouse.location', 'compras.warehouse.inventory',
        }
        warehouse_actions = (
            'purchase_request_authorized_action', 'purchase_request_received_action',
            'compras_supplier_action', 'compras_uom_action',
        )
        action_id = (options or {}).get('action_id')
        shared_action_ids = {
            self.env.ref('Warehouse_Management.' + xmlid).id for xmlid in warehouse_actions
        }
        if self._name not in warehouse_models and action_id not in shared_action_ids:
            return result

        navigation_buttons = {
            'action_open_inventory', 'action_open_location_inventory',
            'action_open_product_location_moves',
        }
        for view_type, view in result['views'].items():
            if view_type not in ('form', 'list', 'kanban'):
                continue
            arch = etree.fromstring(view['arch'])
            for node in arch.xpath('descendant-or-self::form | descendant-or-self::list | descendant-or-self::kanban'):
                node.set('create', '0')
                node.set('edit', '0')
                node.set('delete', '0')
                if node.tag == 'list':
                    node.attrib.pop('editable', None)
            for button in arch.xpath('.//button[@type="object" or @type="action"]'):
                if button.get('name') not in navigation_buttons:
                    button.getparent().remove(button)
            for chatter in arch.xpath('.//chatter | .//*[contains(concat(" ", normalize-space(@class), " "), " oe_chatter ")]'):
                chatter.getparent().remove(chatter)
            for field in arch.xpath('.//field'):
                field.set('can_create', 'false')
                field.set('can_write', 'false')
            view['arch'] = etree.tostring(arch, encoding='unicode')
            if 'toolbar' in view:
                view['toolbar'].pop('action', None)
        return result
