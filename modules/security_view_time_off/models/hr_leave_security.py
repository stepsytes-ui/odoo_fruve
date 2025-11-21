# -*- coding: utf-8 -*-
from datetime import datetime, time, date
from odoo import models, fields, api


class security_view(models.Model):
    _inherit = 'hr.leave' 

    biometric_id = fields.Char(
        string='No. Empleado',
        related='employee_id.biometric_id',
        store=True,
        readonly=True
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

    request_datetime_from = fields.Datetime(
        string='Inicio (Fecha y Hora)',
        compute='_compute_request_datetime',
        store=True  # Almacenar el resultado para que sea más rápido y se pueda ordenar
    )

    request_datetime_to = fields.Datetime(
        string='Fin (Fecha y Hora)',
        compute='_compute_request_datetime',
        store=True
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
                
                # Combinar fecha y hora
                record.request_datetime_from = datetime.combine(record.request_date_from, time_from)
            else:
                record.request_datetime_from = False

            # Combinar Fecha de Fin y Hora de Fin
            if record.request_date_to and record.request_hour_to is not False:
                # Convertir request_hour_to (float) a objeto time()
                hours = int(record.request_hour_to)
                minutes = int((record.request_hour_to - hours) * 60)
                time_to = time(hours, minutes, 0)
                
                # Combinar fecha y hora
                record.request_datetime_to = datetime.combine(record.request_date_to, time_to)
            else:
                record.request_datetime_to = False