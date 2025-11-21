from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.constrains('number_of_days', 'holiday_status_id', 'employee_id', 'state')
    def _check_vacation_availibility_and_update(self):
        
        for leave in self:
            if leave.holiday_status_id.name == 'Vacaciones' and leave.state == 'validate':
                expedient = self.env['employee.expedient'].search([
                    ('employee_id', '=', leave.employee_id.id),
                ], order='fecha_movimiento desc', limit=1)

                if not expedient:
                    raise ValidationError(_("No se encontró un expediente activo para el empleado %s.") % leave.employee_id.name)
                
                days_requested = leave.number_of_days
                days_available = expedient.dias_vacaciones_disponibles

                if days_requested > days_available:
                    raise ValidationError(_(
                        "Error de vacaciones: El empleado %s solo tiene %.2f días disponibles y está solicitando %.2f días"
                    ) % (leave.employee_id.name, days_available, days_requested))

                else:
                    new_used_days = expedient.dias_vacaciones_utilizados + days_requested
                    expedient.write({'dias_vacaciones_utilizados': new_used_days})

                    self.env['mail.message'].create({
                        'model': 'employee.expedient',
                        'res_id': expedient.id,
                        'message_type': 'notification',
                        'body':_("**Descuento de Vacaciones Automático:** Se descontaron %.2f días por la solicitud de ausencias #%s. Saldo anterior: %.2f días. Nuevo Saldo Utilizado: %.2f días."
                        ) % (days_requested, leave.name, days_available, new_used_days),
                        'subject': 'Vacaciones Descontadas',
                        'author_id': self.env.user.partner_id.id,
                    })