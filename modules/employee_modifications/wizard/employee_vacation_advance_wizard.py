from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EmployeeVacationAdvanceWarningWizard(models.TransientModel):
    _name = 'employee.vacation.advance.warning.wizard'
    _description = 'Advertencia para adelantar vacaciones'

    leave_id = fields.Many2one(
        'hr.leave',
        string='Solicitud de Ausencia',
        required=True,
        readonly=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        related='leave_id.employee_id',
        readonly=True,
    )
    days_requested = fields.Float(string='Días Solicitados', readonly=True)
    days_available = fields.Float(string='Días Disponibles', readonly=True)
    shortage_days = fields.Float(string='Días a Adelantar', readonly=True)

    def action_open_advance_days_wizard(self):
        self.ensure_one()
        return {
            'name': _('Adelantar Días de Vacaciones'),
            'type': 'ir.actions.act_window',
            'res_model': 'employee.vacation.advance.days.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'employee_modifications.view_employee_vacation_advance_days_wizard_form'
            ).id,
            'target': 'new',
            'context': {
                'default_leave_id': self.leave_id.id,
                'default_days_requested': self.days_requested,
                'default_days_available': self.days_available,
                'default_shortage_days': self.shortage_days,
                'default_days_to_advance': self.shortage_days,
            },
        }


class EmployeeVacationAdvanceDaysWizard(models.TransientModel):
    _name = 'employee.vacation.advance.days.wizard'
    _description = 'Captura de días adelantados de vacaciones'

    leave_id = fields.Many2one(
        'hr.leave',
        string='Solicitud de Ausencia',
        required=True,
        readonly=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        related='leave_id.employee_id',
        readonly=True,
    )
    days_requested = fields.Float(string='Días Solicitados', readonly=True)
    days_available = fields.Float(string='Días Disponibles', readonly=True)
    shortage_days = fields.Float(string='Faltante Mínimo', readonly=True)
    days_to_advance = fields.Float(
        string='¿Cuántos días desea adelantar?',
        required=True,
        default=0.0,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'days_to_advance' in fields_list and not res.get('days_to_advance'):
            res['days_to_advance'] = res.get('shortage_days', 0.0)
        return res

    def action_confirm_advance_days(self):
        self.ensure_one()

        leave = self.leave_id.exists()
        if not leave:
            raise ValidationError(_('La solicitud de vacaciones ya no existe.'))

        if leave.state not in ['confirm', 'validate1']:
            raise ValidationError(
                _('Solo se pueden adelantar días en solicitudes pendientes de aprobación.')
            )

        if self.days_to_advance <= 0:
            raise ValidationError(_('Debe indicar un número de días mayor a 0.'))

        if self.days_to_advance < self.shortage_days:
            raise ValidationError(_(
                'Debe adelantar al menos %.2f días para poder autorizar esta solicitud.'
            ) % self.shortage_days)

        if self.days_to_advance > self.days_requested:
            raise ValidationError(_(
                'Los días adelantados no pueden ser mayores a los días solicitados (%.2f).'
            ) % self.days_requested)

        leave.write({'advance_vacation_days': self.days_to_advance})
        leave.with_context(skip_vacation_advance_check=True).action_validate()

        return {'type': 'ir.actions.act_window_close'}
