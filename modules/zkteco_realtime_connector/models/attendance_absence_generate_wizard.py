from odoo import models, fields, _


class AttendanceAbsenceGenerateWizard(models.TransientModel):
    _name = 'attendance.absence.generate.wizard'
    _description = 'Wizard para generar faltas por fecha'

    target_date = fields.Date(
        string='Fecha a procesar',
        required=True,
        default=fields.Date.context_today,
        help='Se generarán faltas/permisos para esta fecha específica.'
    )

    def action_generate_absences(self):
        self.ensure_one()

        result = self.env['hr.attendance']._cron_generate_absences(target_date=self.target_date)

        if not result:
            message = _('No se recibió respuesta del proceso de generación de faltas.')
        else:
            message = _(
                'Fecha: %(date)s | Faltas generadas: %(faltas)s | Permisos generados: %(permisos)s'
            ) % {
                'date': result.get('target_date') or self.target_date,
                'faltas': result.get('faltas_generadas', 0),
                'permisos': result.get('permisos_generados', 0),
            }

            if result.get('skipped') and result.get('message'):
                message = result.get('message')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Generación de faltas'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }
