from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeSupervisor(models.Model):
    _name = 'employee.supervisor'
    _description = 'Supervisores por Compania'
    _rec_name = 'display_name'
    _order = 'company_id, employee_id'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        ondelete='cascade',
        domain="[('company_id', '=', company_id)]",
    )

    supervisor_name = fields.Char(
        string='Nombre Supervisor Externo',
        help='Ingresa el nombre completo del supervisor externo si no es un empleado de la empresa',
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

    display_name = fields.Char(
        string='Nombre',
        compute='_compute_display_name',
        store=True,
    )

    _sql_constraints = [
        (
            'employee_supervisor_company_unique',
            'unique(employee_id, company_id) where employee_id is not null',
            'El empleado ya esta configurado como supervisor para esta compania.',
        ),
    ]

    @api.constrains('employee_id', 'supervisor_name')
    def _check_supervisor_selection(self):
        for record in self:
            if not record.employee_id and not record.supervisor_name:
                raise ValidationError(
                    _('Debe seleccionar un Empleado o ingresar el Nombre del Supervisor Externo.')
                )

    @api.constrains('employee_id', 'company_id')
    def _check_employee_company(self):
        for record in self:
            if record.employee_id and record.employee_id.company_id and record.employee_id.company_id != record.company_id:
                raise ValidationError(
                    _('El empleado seleccionado no pertenece a la compania configurada.')
                )

    @api.depends('employee_id', 'supervisor_name')
    def _compute_display_name(self):
        for record in self:
            if record.employee_id:
                record.display_name = record.employee_id.name
            elif record.supervisor_name:
                record.display_name = record.supervisor_name
            else:
                record.display_name = "Sin asignar"
