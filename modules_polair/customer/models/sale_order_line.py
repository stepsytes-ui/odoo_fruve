from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    custom_tax_option_id = fields.Many2one(
        'customer.tax.option',
        string='Impuesto',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        default=lambda self: self.env.user.default_custom_tax_option_id,
    )

    custom_tax_percent = fields.Float(
        string='Impuesto (%)',
        digits=(16, 2),
        default=lambda self: self.env.user.default_custom_tax_percent or 16.0,
        help='Porcentaje de IVA personalizado para esta linea.',
    )

    @api.onchange('custom_tax_option_id')
    def _onchange_custom_tax_option_id(self):
        for line in self:
            if line.custom_tax_option_id:
                line.custom_tax_percent = line.custom_tax_option_id.percent

    tax_id = fields.Many2many(
        comodel_name='account.tax',
        string='Taxes',
        compute='_compute_tax_id',
        store=True,
        readonly=False,
        precompute=True,
        context={'active_test': False},
        check_company=True,
        domain="[('type_tax_use', '=', 'sale'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'custom_tax_percent')
    def _compute_amount(self):
        super()._compute_amount()
        for line in self.filtered(lambda l: not l.display_type):
            tax_amount = line.price_subtotal * ((line.custom_tax_percent or 0.0) / 100.0)
            if line.currency_id:
                tax_amount = line.currency_id.round(tax_amount)
            line.price_tax = tax_amount
            line.price_total = line.price_subtotal + tax_amount

    def _remember_user_custom_tax_percent(self, percent):
        if percent is None:
            return
        self.env.user.sudo().write({'default_custom_tax_percent': percent})

    def _remember_user_custom_tax_option(self, option):
        if option:
            self.env.user.sudo().write({'default_custom_tax_option_id': option.id})

    @api.model_create_multi
    def create(self, vals_list):
        tax_option_model = self.env['customer.tax.option'].sudo()
        lines = super().create(vals_list)
        for vals in vals_list:
            if 'custom_tax_percent' in vals:
                self._remember_user_custom_tax_percent(vals.get('custom_tax_percent'))
            option_id = vals.get('custom_tax_option_id')
            if option_id:
                option = tax_option_model.browse(option_id)
                self._remember_user_custom_tax_option(option)
        return lines

    def write(self, vals):
        tax_option_model = self.env['customer.tax.option'].sudo()
        res = super().write(vals)
        if 'custom_tax_percent' in vals:
            self._remember_user_custom_tax_percent(vals.get('custom_tax_percent'))
        if 'custom_tax_option_id' in vals and vals.get('custom_tax_option_id'):
            option = tax_option_model.browse(vals.get('custom_tax_option_id'))
            self._remember_user_custom_tax_option(option)
        return res
