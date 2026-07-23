from odoo import fields, models


class OvertimeTripleEmployee(models.Model):
    _name = 'overtime.triple.employee'
    _description = 'Empleados con Regla de Hora Triple'
    _order = 'employee_id'

    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        domain="[('company_id', 'in', [company_id, False])]",
        index=True,
    )
    active = fields.Boolean(string='Activo', default=True)
    note = fields.Char(string='Nota')

    _sql_constraints = [
        (
            'overtime_triple_employee_unique',
            'unique(company_id, employee_id)',
            'El empleado ya esta registrado para la regla de hora triple en esta compania.',
        ),
    ]
