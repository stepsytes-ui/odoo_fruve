from odoo import api, fields, models


class ResPartner(models.Model):
	_inherit = 'res.partner'

	customer_auto_id = fields.Integer(
		string='ID Cliente',
		readonly=True,
		copy=False,
		index=True,
	)

	@api.model_create_multi
	def create(self, vals_list):
		partners = super().create(vals_list)
		partners.filtered(lambda partner: (partner.customer_auto_id or 0) <= 0)._assign_customer_auto_id()
		return partners

	def _assign_customer_auto_id(self):
		sequence_model = self.env['ir.sequence']
		for partner in self:
			if (partner.customer_auto_id or 0) > 0:
				continue
			next_value = sequence_model.next_by_code('customer_polair.partner.auto.id')
			if next_value:
				partner.customer_auto_id = int(next_value)
				continue

			# Fallback when the sequence is missing or not initialized.
			last_partner = self.search([
				('id', '!=', partner.id),
				('customer_auto_id', '>', 0),
			], order='customer_auto_id desc', limit=1)
			partner.customer_auto_id = (last_partner.customer_auto_id or 0) + 1

	@api.model
	def _cron_assign_customer_auto_id(self):
		while True:
			partners = self.search([
				('customer_rank', '>', 0),
				('customer_auto_id', '<=', 0),
			], limit=200)
			if not partners:
				break
			partners._assign_customer_auto_id()
