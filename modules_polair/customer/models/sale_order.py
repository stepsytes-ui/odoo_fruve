from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amount_tax = fields.Monetary(string='IVA', store=True, compute='_compute_amounts')

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.display_type')
    def _compute_amounts(self):
        for order in self:
            lines = order.order_line.filtered(lambda l: not l.display_type)
            amount_untaxed = sum(lines.mapped('price_subtotal'))
            amount_tax = sum(lines.mapped('price_tax'))

            currency = order.currency_id or order.company_id.currency_id
            if currency:
                amount_untaxed = currency.round(amount_untaxed)
                amount_tax = currency.round(amount_tax)

            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = amount_untaxed + amount_tax
