# -*- coding: utf-8 -*-

import logging
import pytz
import unicodedata

from odoo import models, fields, api
from odoo.tools.float_utils import float_round
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from odoo.tools import format_date
from datetime import datetime, timedelta, time
from math import ceil

_logger = logging.getLogger(__name__)

class HrLeaveCustom(models.Model):
    """Customización para que Incapacidad cuente días naturales"""
    _inherit = 'hr.leave'

    biometric_id = fields.Char(
        string='Número de Empleado',
        related='employee_id.biometric_id',
        store=True,
        readonly=True
    )

    biometric_id_numeric = fields.Integer(
        string='No. Empleado',
        related='employee_id.biometric_id_numeric',
        store=True,
        readonly=True,
        help='Campo numérico para ordenamiento'
    )

    def _normalize_leave_type_name(self, leave_type_name):
        normalized = (leave_type_name or '').strip().lower()
        normalized = unicodedata.normalize('NFKD', normalized)
        normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
        return ' '.join(normalized.split())

    def _is_natural_day_leave(self, leave):
        """Permisos que ignoran horario/calendario y cuentan dias naturales."""
        leave_name_key = self._normalize_leave_type_name(leave.holiday_status_id.name)
        return leave_name_key in {'incapacidad', 'permiso por cumpleanos'}

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Permite buscar ausencias por nombre de empleado o biometric_id
        """
        args = args or []
        
        if not name:
            return super().name_search(name=name, args=args, operator=operator, limit=limit)
        
        # Si el nombre es numérico, buscar por biometric_id
        if name.isdigit():
            domain = [
                '|',
                ('employee_id.biometric_id', 'ilike', name),
                ('employee_id.name', operator, name)
            ]
        else:
            domain = [
                '|',
                ('employee_id.name', operator, name),
                ('employee_id.biometric_id', operator, name)
            ]
        
        leave_ids = self._search(args + domain, limit=limit)
        return self.browse(leave_ids).name_get()

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date(self):
        """Sobrescribir validación para permitir permisos de horas y días en el mismo día"""
        if self.env.context.get('leave_skip_date_check', False):
            return

        all_leaves = self.search([
            ('date_from', '<', max(self.mapped('date_to'))),
            ('date_to', '>', min(self.mapped('date_from'))),
            ('employee_id', 'in', self.employee_id.ids),
            ('id', 'not in', self.ids),
            ('state', 'not in', ['cancel', 'refuse']),
        ])
        
        for holiday in self:
            # Las incapacidades pueden sobreponerse sobre cualquier otro permiso.
            if self._is_natural_day_leave(holiday):
                continue

            domain = [
                ('employee_id', '=', holiday.employee_id.id),
                ('date_from', '<', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
            ]
            conflicting_holidays = all_leaves.filtered_domain(domain)

            # Filtrar solo permisos que tienen la misma unidad de medida (hora o día)
            # Esto permite tener un permiso de horas y uno de días en el mismo día
            same_unit_conflicts = conflicting_holidays.filtered(
                lambda h: h.leave_type_request_unit == holiday.leave_type_request_unit
            )

            if same_unit_conflicts:
                conflicting_holidays_list = []
                holidays_only_have_uid = bool(holiday.employee_id)
                holiday_states = dict(same_unit_conflicts.fields_get(allfields=['state'])['state']['selection'])
                
                for conflicting_holiday in same_unit_conflicts:
                    conflicting_holiday_data = {}
                    conflicting_holiday_data['employee_name'] = conflicting_holiday.employee_id.name
                    conflicting_holiday_data['date_from'] = format_date(self.env, min(conflicting_holiday.mapped('date_from')))
                    conflicting_holiday_data['date_to'] = format_date(self.env, min(conflicting_holiday.mapped('date_to')))
                    conflicting_holiday_data['state'] = holiday_states[conflicting_holiday.state]
                    if conflicting_holiday.employee_id.user_id.id != self.env.uid:
                        holidays_only_have_uid = False
                    if conflicting_holiday_data not in conflicting_holidays_list:
                        conflicting_holidays_list.append(conflicting_holiday_data)
                
                if not conflicting_holidays_list:
                    return
                
                conflicting_holidays_strings = []
                if holidays_only_have_uid:
                    for conflicting_holiday_data in conflicting_holidays_list:
                        conflicting_holidays_string = _('from %(date_from)s to %(date_to)s - %(state)s',
                                                        date_from=conflicting_holiday_data['date_from'],
                                                        date_to=conflicting_holiday_data['date_to'],
                                                        state=conflicting_holiday_data['state'])
                        conflicting_holidays_strings.append(conflicting_holidays_string)
                    raise ValidationError(_("""\
You've already booked time off which overlaps with this period:
%s
Attempting to double-book your time off won't magically make your vacation 2x better!
""",
                        "\n".join(conflicting_holidays_strings)))
                
                for conflicting_holiday_data in conflicting_holidays_list:
                    conflicting_holidays_string = "\n" + _('%(employee_name)s - from %(date_from)s to %(date_to)s - %(state)s',
                                                    employee_name=conflicting_holiday_data['employee_name'],
                                                    date_from=conflicting_holiday_data['date_from'],
                                                    date_to=conflicting_holiday_data['date_to'],
                                                    state=conflicting_holiday_data['state'])
                    conflicting_holidays_strings.append(conflicting_holidays_string)
                raise ValidationError(_(
                    "An employee already booked time off which overlaps with this period:%s",
                    "".join(conflicting_holidays_strings)))

    @api.depends('date_from', 'date_to', 'resource_calendar_id', 'holiday_status_id.request_unit', 'holiday_status_id', 'request_date_from', 'request_date_to')
    def _compute_duration(self):
        # Base: comportamiento estandar de Odoo.
        super()._compute_duration()

        # Ajuste: para Incapacidad/Cumpleanos, contar dias naturales aunque no haya jornada laboral.
        for leave in self:
            if not self._is_natural_day_leave(leave):
                continue

            if leave.leave_type_request_unit == 'hour':
                continue

            if leave.request_date_from and leave.request_date_to:
                natural_days = (leave.request_date_to - leave.request_date_from).days + 1
                leave.number_of_days = max(natural_days, 0)

    @api.depends('number_of_hours', 'number_of_days', 'leave_type_request_unit', 'holiday_status_id', 'request_date_from', 'request_date_to')
    def _compute_duration_display(self):
        # Primero, llamar al método padre para calcular el valor por defecto
        super()._compute_duration_display()
        
        # Luego, modificar para permisos que cuentan dias naturales.
        for leave in self:
            if self._is_natural_day_leave(leave) and leave.request_date_from and leave.request_date_to:
                # Contar días naturales (sin considerar el calendario laboral)
                date_from = leave.request_date_from
                date_to = leave.request_date_to
                
                # Calcular la diferencia en días naturales
                delta = date_to - date_from
                natural_days = delta.days + 1  # +1 para incluir ambos días
                
                if leave.leave_type_request_unit == "hour":
                    # Si es por horas, mantener la lógica original
                    hours, minutes = divmod(abs(leave.number_of_hours) * 60, 60)
                    minutes = round(minutes)
                    if minutes == 60:
                        minutes = 0
                        hours += 1
                    duration = '%d:%02d' % (hours, minutes)
                    unit = _("horas")
                    leave.duration_display = f"{duration} {unit}"
                else:
                    # Para días, mostrar los días naturales
                    unit = _('días')
                    display = "%g %s" % (float_round(natural_days, precision_digits=2), unit)
                    leave.duration_display = display

    def action_validate(self, check_state=True):
        result = super().action_validate(check_state)
        self.filtered(lambda l: l.state == 'validate')._retroactively_fix_vacation_absences()
        return result

    def _retroactively_fix_vacation_absences(self):
        """
        Cuando se valida un permiso de Vacaciones, busca registros de asistencia
        con estatus 'absence' del empleado dentro del rango de fechas del permiso
        y los convierte a 'leave_vacation', corrigiendo el cálculo de neto.
        """
        for leave in self:
            if leave.holiday_status_id.name != 'Vacaciones':
                continue
            if not leave.employee_id or not leave.date_from or not leave.date_to:
                continue

            # Comparar por día completo local para evitar desajustes por horas del turno.
            company_tz_name = leave.employee_id.company_id.timezone or 'UTC'
            try:
                company_tz = pytz.timezone(company_tz_name)
            except pytz.UnknownTimeZoneError:
                company_tz = pytz.utc

            start_date = leave.request_date_from or fields.Date.to_date(leave.date_from)
            end_date = leave.request_date_to or fields.Date.to_date(leave.date_to)

            day_start_local = company_tz.localize(datetime.combine(start_date, time.min))
            day_end_local = company_tz.localize(datetime.combine(end_date, time.max))

            day_start_utc = day_start_local.astimezone(pytz.utc)
            day_end_utc = day_end_local.astimezone(pytz.utc)

            absence_records = self.env['hr.attendance'].search([
                ('employee_id', '=', leave.employee_id.id),
                ('punctuality_status', '=', 'absence'),
                ('check_in', '>=', fields.Datetime.to_string(day_start_utc)),
                ('check_in', '<=', fields.Datetime.to_string(day_end_utc)),
            ])

            if not absence_records:
                continue

            count = len(absence_records)
            absence_records.with_context(skip_attendance_sync=True).write({
                'punctuality_status': 'leave_vacation',
            })
            _logger.info(
                "[VACATION FIX] Se corrigieron %s faltas a 'leave_vacation' para %s "
                "en el rango %s - %s.",
                count,
                leave.employee_id.name,
                day_start_utc,
                day_end_utc,
            )
