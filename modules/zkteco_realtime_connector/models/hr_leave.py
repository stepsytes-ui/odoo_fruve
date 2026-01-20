# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.float_utils import float_round
from odoo.tools.translate import _
from datetime import datetime, timedelta
from math import ceil

class HrLeaveCustom(models.Model):
    """Customización para que Incapacidad cuente días naturales"""
    _inherit = 'hr.leave'

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
