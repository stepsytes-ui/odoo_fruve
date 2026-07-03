from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeSupervisor(models.Model):
    _name = 'employee.supervisor'
    _description = 'Supervisores por Compania'
    _rec_name = 'employee_id'
    _order = 'company_id, employee_id'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        ondelete='cascade',
        domain="[('company_id', '=', company_id)]",
    )

    biometric_id = fields.Char(
        string='No. Empleado',
        related='employee_id.biometric_id',
        store=True,
        readonly=True,
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Departamento',
        related='employee_id.department_id',
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
    )

    active = fields.Boolean(
        string='Activo',
        default=True,
    )

    _sql_constraints = [
        (
            'employee_supervisor_company_unique',
            'unique(employee_id, company_id)',
            'El empleado ya esta configurado como supervisor para esta compania.',
        ),
    ]

    @api.constrains('employee_id', 'company_id')
    def _check_employee_company(self):
        for record in self:
            if record.employee_id.company_id and record.employee_id.company_id != record.company_id:
                raise ValidationError(
                    _('El empleado seleccionado no pertenece a la compania configurada.')
                )
