# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.float_utils import float_round
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from odoo.tools import format_date
from datetime import datetime, timedelta
from math import ceil

class HrLeaveCustom(models.Model):
    """Customización para que Incapacidad cuente días naturales"""
    _inherit = 'hr.leave'

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

    @api.depends('number_of_hours', 'number_of_days', 'leave_type_request_unit', 'holiday_status_id', 'request_date_from', 'request_date_to')
    def _compute_duration_display(self):
        # Primero, llamar al método padre para calcular el valor por defecto
        super()._compute_duration_display()
        
        # Luego, modificar solo para Incapacidad
        for leave in self:
            if leave.holiday_status_id.name == 'Incapacidad' and leave.request_date_from and leave.request_date_to:
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
