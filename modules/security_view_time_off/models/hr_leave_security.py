# -*- coding: utf-8 -*-
from datetime import datetime, time, date
import math
import pytz
from odoo import models, fields, api
from odoo.exceptions import UserError


class security_view(models.Model):
    _inherit = 'hr.leave' 

    biometric_id = fields.Char(
        string='No. Empleado',
        related='employee_id.biometric_id',
        store=True,
        readonly=True
    )

    punctuality_status = fields.Selection([
        ('leave_abscent', 'Permiso de ausencia'),
        ('leave_hours', 'Permiso por horas'),
        ('leave_hours_paid', 'Permiso pagado por horas'),
        ('leave_delay_pass_paid', 'Permiso retardo'),
        ('leave_partial_paid', 'Permiso parcial pagado'),
        ('leave_partial_unpaid', 'Permiso parcial no pagado'),
    ], string='Etiqueta de Permiso', default='leave_hours')

    check_in_time = fields.Datetime(
        string='Hora de Entrada (Verificación)',
        help='Se captura cuando se registra la entrada del permiso'
    )

    check_out_time = fields.Datetime(
        string='Hora de Salida (Verificación)',
        help='Se captura cuando se registra la salida del permiso'
    )

    description_security = fields.Text(
        string='Motivo Visible',
        compute='_compute_description_security',
        store=False,
        readonly=True
    )

    # Campo relacionado para la imagen del empleado
    employee_image = fields.Image(
        related='employee_id.image_1920',
        string='Foto',
        readonly=True,
        store=False, # No es necesario almacenar ya que es related
    )

    request_datetime_from = fields.Char(
        string='Inicio (Fecha y Hora)',
        compute='_compute_request_datetime',
        store=False
    )

    request_datetime_to = fields.Char(
        string='Fin (Fecha y Hora)',
        compute='_compute_request_datetime',
        store=False
    )

    display_duration = fields.Char(
        string='Duración',
        compute='_compute_display_duration',
        store=False
    )
                
    @api.depends('request_date_from', 'request_hour_from', 'request_date_to', 'request_hour_to')
    def _compute_request_datetime(self):
        for record in self:
            # Combinar Fecha de Inicio y Hora de Inicio
            if record.request_date_from and record.request_hour_from is not False:
                # Convertir request_hour_from (float) a objeto time()
                hours = int(record.request_hour_from)
                minutes = int((record.request_hour_from - hours) * 60)
                time_from = time(hours, minutes, 0)
                
                # Combinar fecha y hora y formatear como string
                dt = datetime.combine(record.request_date_from, time_from)
                record.request_datetime_from = dt.strftime('%d/%m/%Y %H:%M:%S')
            else:
                record.request_datetime_from = ''

            # Combinar Fecha de Fin y Hora de Fin
            if record.request_date_to and record.request_hour_to is not False:
                # Convertir request_hour_to (float) a objeto time()
                hours = int(record.request_hour_to)
                minutes = int((record.request_hour_to - hours) * 60)
                time_to = time(hours, minutes, 0)
                
                # Combinar fecha y hora y formatear como string
                dt = datetime.combine(record.request_date_to, time_to)
                record.request_datetime_to = dt.strftime('%d/%m/%Y %H:%M:%S')
            else:
                record.request_datetime_to = ''

    @api.depends('request_date_from', 'request_hour_from', 'request_date_to', 'request_hour_to', 'number_of_days', 'request_unit_half', 'request_unit_hours')
    def _compute_display_duration(self):
        for record in self:

            if record.request_unit_hours and record.request_date_from and record.request_date_to and record.request_hour_from is not False and record.request_hour_to is not False:
                # Calcular diferencia usando los campos originales
                hours_from = int(record.request_hour_from)
                minutes_from = int((record.request_hour_from - hours_from) * 60)
                time_from = time(hours_from, minutes_from, 0)
                datetime_from = datetime.combine(record.request_date_from, time_from)
                
                hours_to = int(record.request_hour_to)
                minutes_to = int((record.request_hour_to - hours_to) * 60)
                time_to = time(hours_to, minutes_to, 0)
                datetime_to = datetime.combine(record.request_date_to, time_to)
                
                time_delta = datetime_to - datetime_from
                total_seconds = time_delta.total_seconds()
                total_hours = total_seconds / 3600.0
                
                rounded_hours = fields.float_round(total_hours, precision_digits=2)
                
                record.display_duration = f"{rounded_hours} horas"
            
            elif not record.request_unit_hours and record.number_of_days:
                if record.number_of_days == math.floor(record.number_of_days):
                    record.display_duration = f"{int(record.number_of_days)} día(s)"
                else:
                    rounded_days = fields.float_round(record.number_of_days, precision_digits=1)
                    record.display_duration = f"{rounded_days} día(s)"
            
            else:
                record.display_duration = "0 día(s)"

    def action_check_in(self):
        """Registra la hora de entrada del permiso. Solo se puede hacer si no hay entrada registrada."""
        self.ensure_one()
        if self.check_in_time:
            raise UserError('La entrada ya fue registrada. Hora: {}'.format(self.check_in_time))
        self.sudo().write({
            'check_in_time': fields.Datetime.now()
        })

    def action_check_out(self):
        """Registra la hora de salida del permiso. Requiere que check_in haya sido registrado."""
        self.ensure_one()
        if not self.check_in_time:
            raise UserError('Debe registrar la entrada antes de registrar la salida.')
        if self.check_out_time:
            raise UserError('La salida ya fue registrada. Hora: {}'.format(self.check_out_time))
        self.sudo().write({
            'check_out_time': fields.Datetime.now()
        })