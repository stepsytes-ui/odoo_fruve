# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class ComprasProductAlertWizard(models.TransientModel):
    _name = 'compras.product.alert.wizard'
    _description = 'Alertas de productos de compras'

    line_ids = fields.One2many(
        'compras.product.alert.wizard.line',
        'wizard_id',
        string='Alertas',
        readonly=True,
    )
    min_alert_count = fields.Integer(string='Productos al mínimo', readonly=True)
    expiration_alert_count = fields.Integer(string='Productos por caducar', readonly=True)
    total_alert_count = fields.Integer(string='Total de alertas', readonly=True)

    @api.model
    def _get_product_stock_map(self, product_ids, company_ids):
        stock_map = {product_id: 0.0 for product_id in product_ids}
        if not product_ids:
            return stock_map

        inventory_model = self.env['compras.warehouse.inventory'].sudo().with_context(
            allowed_company_ids=company_ids,
        )
        grouped_lines = inventory_model.read_group(
            [
                ('product_id', 'in', product_ids),
                ('company_id', 'in', company_ids),
            ],
            ['product_id', 'quantity:sum'],
            ['product_id'],
        )
        for line in grouped_lines:
            product_data = line.get('product_id')
            if not product_data:
                continue
            stock_map[product_data[0]] = line.get('quantity', 0.0)
        return stock_map

    @api.model
    def action_open_current_user_wizard(self):
        user = self.env.user
        if not (
            user.has_group('compras_fruvemex.group_compras_encargado')
            or user.has_group('compras_fruvemex.group_compras_almacenista')
        ):
            return False

        company_ids = self.env.companies.ids or [self.env.company.id]
        product_model = self.env['compras.product'].sudo().with_context(
            allowed_company_ids=company_ids,
        )
        today = fields.Date.context_today(self)
        expiration_limit = today + relativedelta(months=1)

        candidate_min_stock_products = product_model.search([
            ('active', '=', True),
            ('company_id', 'in', company_ids),
            ('min_qty', '>', 0),
        ])
        stock_map = self._get_product_stock_map(candidate_min_stock_products.ids, company_ids)
        min_stock_products = candidate_min_stock_products.filtered(
            lambda product: stock_map.get(product.id, 0.0) <= product.min_qty
        )

        expiration_products = product_model.search([
            ('active', '=', True),
            ('company_id', 'in', company_ids),
            ('expiration_date', '!=', False),
            ('expiration_date', '>=', today),
            ('expiration_date', '<=', expiration_limit),
        ])

        alert_map = {}
        for product in min_stock_products:
            alert_map[product.id] = {
                'product_id': product.id,
                'code': product.code or '',
                'name': product.name or '',
                'qty_on_hand': stock_map.get(product.id, 0.0),
                'min_qty': product.min_qty,
                'expiration_date': product.expiration_date,
                'days_to_expire': False,
                'alert_min_qty': True,
                'alert_expiration': False,
                'alert_reason': _('Stock al mínimo'),
            }

        for product in expiration_products:
            days_to_expire = (product.expiration_date - today).days if product.expiration_date else False
            existing = alert_map.get(product.id)
            if existing:
                existing['alert_expiration'] = True
                existing['expiration_date'] = product.expiration_date
                existing['days_to_expire'] = days_to_expire
                existing['alert_reason'] = _('Stock al mínimo y caducidad próxima')
            else:
                alert_map[product.id] = {
                    'product_id': product.id,
                    'code': product.code or '',
                    'name': product.name or '',
                    'qty_on_hand': stock_map.get(product.id, 0.0),
                    'min_qty': product.min_qty,
                    'expiration_date': product.expiration_date,
                    'days_to_expire': days_to_expire,
                    'alert_min_qty': False,
                    'alert_expiration': True,
                    'alert_reason': _('Caducidad próxima'),
                }

        if not alert_map:
            return False

        wizard = self.sudo().create({
            'min_alert_count': sum(1 for item in alert_map.values() if item['alert_min_qty']),
            'expiration_alert_count': sum(1 for item in alert_map.values() if item['alert_expiration']),
            'total_alert_count': len(alert_map),
            'line_ids': [(0, 0, values) for values in sorted(
                alert_map.values(),
                key=lambda values: (
                    0 if values['alert_expiration'] else 1,
                    values['days_to_expire'] if values['days_to_expire'] is not False else 9999,
                    values['name'],
                ),
            )],
        })

        action = self.env.ref('compras_fruvemex.compras_product_alert_wizard_action').sudo().read()[0]
        action['res_id'] = wizard.id
        action['views'] = [(self.env.ref('compras_fruvemex.compras_product_alert_wizard_form').sudo().id, 'form')]
        action['target'] = 'new'
        return action


class ComprasProductAlertWizardLine(models.TransientModel):
    _name = 'compras.product.alert.wizard.line'
    _description = 'Línea de alerta de producto'

    wizard_id = fields.Many2one(
        'compras.product.alert.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one('compras.product', string='Producto', readonly=True)
    code = fields.Char(string='Código', readonly=True)
    name = fields.Char(string='Descripción', readonly=True)
    alert_reason = fields.Char(string='Motivo', readonly=True)
    qty_on_hand = fields.Float(string='Inventario', readonly=True)
    min_qty = fields.Float(string='Mínimo', readonly=True)
    expiration_date = fields.Date(string='Fecha de caducidad', readonly=True)
    days_to_expire = fields.Integer(string='Días para caducar', readonly=True)
    alert_min_qty = fields.Boolean(string='Stock al mínimo', readonly=True)
    alert_expiration = fields.Boolean(string='Caducidad próxima', readonly=True)