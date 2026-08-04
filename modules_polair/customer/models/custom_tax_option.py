from odoo import api, fields, models


class CustomerTaxOption(models.Model):
    _name = 'customer.tax.option'
    _description = 'Opciones de impuesto personalizado'
    _order = 'sequence, percent'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Nombre', required=True)
    percent = fields.Float(string='Porcentaje', required=True, digits=(16, 2))
    company_id = fields.Many2one('res.company', string='Compania', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('customer_tax_option_name_company_uniq', 'unique(name, company_id)', 'Ya existe una opcion con este nombre para la compania.'),
    ]

    @api.onchange('percent')
    def _onchange_percent(self):
        if self.percent and (not self.name or self.name.endswith('%')):
            self.name = f"{self.percent:g}%"
