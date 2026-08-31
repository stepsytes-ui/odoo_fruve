import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

FIXED_DEVICE_TIMEZONE_NAME = 'America/Tijuana'


class AttendanceJustifyWizard(models.TransientModel):
    _name = 'attendance.justify.wizard'
    _description = 'Wizard para justificar asistencias desfasadas por apagón/falta de internet'

    turno_id = fields.Many2one(
        comodel_name='shift.management',
        string='Turno',
        required=True,
        help='Empleados asignados a este turno serán evaluados.'
    )

    date_to_justify = fields.Date(
        string='Día a Justificar',
        required=True,
        help='Día en el que no se registraron checadas correctamente (ej. día del apagón).'
    )

    date_displaced_checks = fields.Date(
        string='Día de Checadas Desfasadas',
        required=True,
        help='Día donde quedaron registradas las checadas desfasadas (normalmente el día en que volvió el internet).'
    )

    def _get_employee_tz(self, employee):
        company_tz_name = employee.company_id.timezone or FIXED_DEVICE_TIMEZONE_NAME
        try:
            return pytz.timezone(company_tz_name)
        except pytz.UnknownTimeZoneError:
            return pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)

    def _get_day_bounds_utc(self, target_date, employee_tz):
        day_start_local = employee_tz.localize(datetime.combine(target_date, time.min))
        day_end_local = employee_tz.localize(datetime.combine(target_date, time.max))
        return day_start_local.astimezone(pytz.utc), day_end_local.astimezone(pytz.utc)

    def _get_shift_times_for_date(self, employee, target_date):
        """Reutiliza la conversión de horas de turno definida en zkteco.attendance.log."""
        return self.env['zkteco.attendance.log']._get_shift_times(
            employee, datetime.combine(target_date, time.min), None
        )

    def action_justify_attendances(self):
        self.ensure_one()

        if self.date_to_justify == self.date_displaced_checks:
            raise UserError(_('El día a justificar y el día de checadas desfasadas no pueden ser el mismo.'))

        Employee = self.env['hr.employee'].sudo()
        Attendance = self.env['hr.attendance'].sudo()

        employees = Employee.search([
            ('turno_id', '=', self.turno_id.id),
            ('employee_status', '=', 'active'),
        ])

        justified_count = 0
        skipped_has_attendance = 0
        skipped_invalid_count = 0
        skipped_no_shift = 0

        for employee in employees:
            employee_tz = self._get_employee_tz(employee)

            target_start_utc, target_end_utc = self._get_day_bounds_utc(self.date_to_justify, employee_tz)
            already_has_attendance = Attendance.search_count([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', fields.Datetime.to_string(target_start_utc)),
                ('check_in', '<=', fields.Datetime.to_string(target_end_utc)),
            ])
            if already_has_attendance:
                skipped_has_attendance += 1
                continue

            source_start_utc, source_end_utc = self._get_day_bounds_utc(self.date_displaced_checks, employee_tz)
            records = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', fields.Datetime.to_string(source_start_utc)),
                ('check_in', '<=', fields.Datetime.to_string(source_end_utc)),
            ], order='check_in asc')

            count = len(records)
            if count not in (2, 3, 4, 5):
                skipped_invalid_count += 1
                continue

            if count in (4, 5):
                records[-2:].with_context(skip_attendance_sync=True).unlink()
                records = records[:-2]
                count = len(records)

            shift_in_target_utc, shift_out_target_utc = self._get_shift_times_for_date(employee, self.date_to_justify)
            if not shift_in_target_utc or not shift_out_target_utc:
                skipped_no_shift += 1
                continue

            rec1, rec2 = records[0], records[1]
            rec1.with_context(skip_attendance_sync=True).write({
                'check_in': fields.Datetime.to_string(shift_in_target_utc),
                'check_out': fields.Datetime.to_string(shift_out_target_utc),
                'punctuality_status': 'on_time',
            })
            rec2.with_context(skip_attendance_sync=True).write({
                'check_in': fields.Datetime.to_string(shift_out_target_utc),
                'check_out': fields.Datetime.to_string(shift_out_target_utc + timedelta(seconds=1)),
                'punctuality_status': 'end',
            })

            if count == 3:
                shift_in_source_utc, _unused = self._get_shift_times_for_date(employee, self.date_displaced_checks)
                rec3 = records[2]
                rec3.with_context(skip_attendance_sync=True).write({
                    'check_in': fields.Datetime.to_string(shift_in_source_utc) if shift_in_source_utc else rec3.check_in,
                    'check_out': False,
                    'punctuality_status': 'on_time',
                })

            justified_count += 1
            _logger.info(
                "[JUSTIFY ATTENDANCE] Empleado %s justificado. Día: %s, checadas origen: %s.",
                employee.name, self.date_to_justify, self.date_displaced_checks,
            )

        message = _(
            'Empleados justificados: %(justified)s | '
            'Ya tenían checada ese día: %(has_att)s | '
            'Sin turno configurado: %(no_shift)s | '
            'Cantidad de checadas no soportada: %(invalid)s'
        ) % {
            'justified': justified_count,
            'has_att': skipped_has_attendance,
            'no_shift': skipped_no_shift,
            'invalid': skipped_invalid_count,
        }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Justificar Asistencias'),
                'message': message,
                'type': 'success',
                'sticky': True,
            }
        }
