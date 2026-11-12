from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user
from lxml import etree


class TestWarehouseAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env['compras.warehouse'].create({
            'name': 'Almacén de prueba',
            'code': 'ACCESS-TEST',
            'company_id': cls.company.id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Solicitante de prueba',
            'company_id': cls.company.id,
        })
        cls.request = cls.env['purchase.request'].create({
            'company_id': cls.company.id,
            'warehouse_id': cls.warehouse.id,
            'solicitante_id': cls.employee.id,
        })
        cls.product = cls.env['compras.product'].create({
            'name': 'Producto de prueba',
            'company_id': cls.company.id,
        })
        cls.move = cls.env['compras.inventory.move'].create({
            'company_id': cls.company.id,
            'product_id': cls.product.id,
            'request_id': cls.request.id,
            'move_type': 'entrada',
            'destination_warehouse_id': cls.warehouse.id,
        })
        cls.admin = new_test_user(
            cls.env,
            login='warehouse_access_admin',
            groups='base.group_system,Warehouse_Management.group_compras_usuario',
            company_id=cls.company.id,
        )
        cls.warehouse_user = new_test_user(
            cls.env,
            login='warehouse_access_user',
            groups='Warehouse_Management.group_compras_usuario,Warehouse_Management.group_compras_almacenista',
            company_id=cls.company.id,
        )
        cls.purchase_user = new_test_user(
            cls.env,
            login='warehouse_access_purchase',
            groups='Warehouse_Management.group_compras_usuario',
            company_id=cls.company.id,
        )

    def test_movements_can_read_other_users_request(self):
        for user in (self.admin, self.warehouse_user):
            with self.subTest(user=user.login):
                result = self.env['compras.inventory.move'].with_user(user).web_search_read(
                    [('id', '=', self.move.id)],
                    {'name': {}, 'request_id': {'fields': {'name': {}}}},
                )
                self.assertEqual(result['records'][0]['request_id']['id'], self.request.id)

        with self.assertRaises(AccessError):
            self.request.with_user(self.purchase_user).read(['name'])

    def test_warehouse_user_can_receive_other_users_request(self):
        self.request.with_user(self.warehouse_user).write({'comments': 'Recibida en almacén'})
        with self.assertRaises(AccessError):
            self.request.with_user(self.purchase_user).write({'comments': 'Sin acceso'})

    def test_request_access_remains_company_scoped(self):
        other_company = self.env['res.company'].create({'name': 'Otra empresa de prueba'})
        other_warehouse = self.env['compras.warehouse'].create({
            'name': 'Otro almacén',
            'code': 'OTHER-ACCESS',
            'company_id': other_company.id,
        })
        other_employee = self.env['hr.employee'].create({
            'name': 'Otro solicitante',
            'company_id': other_company.id,
        })
        other_request = self.env['purchase.request'].create({
            'company_id': other_company.id,
            'warehouse_id': other_warehouse.id,
            'solicitante_id': other_employee.id,
        })
        for user in (self.admin, self.warehouse_user):
            with self.subTest(user=user.login), self.assertRaises(AccessError):
                other_request.with_user(user).read(['name'])

    def test_warehouse_catalog_creation_and_tools_access(self):
        user = self.warehouse_user
        brand = self.env['product.brand'].with_user(user).create({'name': 'Marca de prueba'})
        self.assertTrue(brand.id)
        material = self.env['compras.packaging.material'].with_user(user).create({
            'name': 'Material de prueba',
        })
        product = self.env['compras.product'].with_user(user).create({
            'name': 'Producto de almacén',
            'code': 'ACCESS-PRODUCT',
            'company_id': self.company.id,
            'brand_id': brand.id,
            'packaging_material_id': material.id,
        })
        warehouse = self.env['compras.warehouse'].with_user(user).create({
            'name': 'Almacén nuevo',
            'code': 'ACCESS-NEW',
            'company_id': self.company.id,
        })
        move = self.env['compras.inventory.move'].with_user(user).create({
            'company_id': self.company.id,
            'product_id': product.id,
            'move_type': 'entrada',
            'destination_warehouse_id': warehouse.id,
        })
        self.assertTrue(move.id)
        wizard = self.env['warehouse.generate.sample.data'].with_user(user).create({})
        self.assertTrue(wizard.id)
        menu = self.env.ref('Warehouse_Management.menu_almacen_generate_data')
        self.assertIn(menu.id, self.env['ir.ui.menu'].with_user(user)._visible_menu_ids())

    def test_warehouse_only_user_cannot_create_purchase_requests(self):
        user = new_test_user(
            self.env,
            login='warehouse_access_only',
            groups='Warehouse_Management.group_compras_almacenista',
            company_id=self.company.id,
        )
        with self.assertRaises(AccessError):
            self.env['purchase.request'].with_user(user).create({
                'company_id': self.company.id,
                'warehouse_id': self.warehouse.id,
                'solicitante_id': self.employee.id,
            })

    def test_viewer_restrictions_override_warehouse_roles(self):
        for groups in (
            'Warehouse_Management.group_almacen_solo_visualizacion',
            'Warehouse_Management.group_almacen_solo_visualizacion,Warehouse_Management.group_compras_encargado',
        ):
            user = new_test_user(
                self.env,
                login='viewer_' + str(len(groups)),
                groups=groups,
                company_id=self.company.id,
            )
            self.assertEqual(self.move.with_user(user).read(['name'])[0]['id'], self.move.id)
            self.assertEqual(self.request.with_user(user).read(['name'])[0]['id'], self.request.id)
            for operation in (
                lambda: self.product.with_user(user).write({'name': 'Modificado'}),
                lambda: self.move.with_user(user).unlink(),
                lambda: self.env['compras.warehouse'].with_user(user).create({
                    'name': 'No permitido', 'code': 'DENIED', 'company_id': self.company.id,
                }),
            ):
                with self.assertRaises(AccessError):
                    operation()

            visible_menus = self.env['ir.ui.menu'].with_user(user)._visible_menu_ids()
            for xmlid in ('menu_almacen_salidas', 'menu_almacen_import_excel',
                          'menu_almacen_reports', 'menu_almacen_generate_data'):
                self.assertIn(self.env.ref('Warehouse_Management.' + xmlid).id, visible_menus)

            sample = self.env['warehouse.generate.sample.data'].with_user(user).create({})
            excel = self.env['compras.product.excel.import.wizard'].with_user(user).create({})
            with self.assertRaises(AccessError):
                sample.action_generate_data()
            with self.assertRaises(AccessError):
                excel.action_import_excel()
            with self.assertRaises(AccessError):
                excel.action_update_inventory_excel()
            self.assertEqual(excel.action_download_template()['type'], 'ir.actions.act_url')
            report = self.env['warehouse.report.wizard'].with_user(user).create({})
            self.assertEqual(report.action_view_report()['type'], 'ir.actions.act_url')

    def test_viewer_can_read_product_alerts(self):
        user = new_test_user(
            self.env,
            login='warehouse_alert_viewer',
            groups='Warehouse_Management.group_almacen_solo_visualizacion',
            company_id=self.company.id,
        )
        self.product.expiration_date = fields.Date.today() + timedelta(days=1)
        action = self.env['compras.product.alert.wizard'].with_user(user).action_open_current_user_wizard()
        wizard = self.env['compras.product.alert.wizard'].with_user(user).browse(action['res_id'])
        self.assertIn(self.product.id, wizard.line_ids.mapped('product_id').ids)

    def test_viewer_warehouse_views_are_readonly_but_purchase_access_is_preserved(self):
        user = new_test_user(
            self.env,
            login='warehouse_viewer_manager',
            groups='Warehouse_Management.group_almacen_solo_visualizacion,Warehouse_Management.group_compras_encargado',
            company_id=self.company.id,
        )
        view = self.env.ref('Warehouse_Management.purchase_request_view_form')
        model = self.env['purchase.request'].with_user(user)
        warehouse_action = self.env.ref('Warehouse_Management.purchase_request_authorized_action')
        purchase_action = self.env.ref('Warehouse_Management.purchase_request_action')
        warehouse_view = model.get_views([(view.id, 'form')], {'action_id': warehouse_action.id})
        purchase_view = model.get_views([(view.id, 'form')], {'action_id': purchase_action.id})
        warehouse_arch = etree.fromstring(warehouse_view['views']['form']['arch'])
        purchase_arch = etree.fromstring(purchase_view['views']['form']['arch'])
        self.assertEqual(warehouse_arch.get('edit'), '0')
        self.assertFalse(warehouse_arch.xpath('.//button[@type="object"]'))
        self.assertNotEqual(purchase_arch.get('edit'), '0')
        self.request.with_user(user).write({'comments': 'Edición desde compras'})
