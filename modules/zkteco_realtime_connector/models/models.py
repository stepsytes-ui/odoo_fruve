# -*- coding: utf-8 -*-

import pytz
import logging
from datetime import datetime, timedelta, time
from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

FIXED_DEVICE_TIMEZONE_NAME = 'America/Tijuana'
TIME_OFFSET_MINUTES = 5
SECOND_DIFFERENCE = 1

class ZkTecoAttendanceLog(models.Model):
    _name = 'zkteco.attendance.log'
    _description = 'Raw Attendance Logs from ZKTeco Device'
    _order = 'timestamp desc'

    device_id = fields.Char(string='Device ID')
    user_id = fields.Char(string='User ID (Biometric)')
    timestamp = fields.Datetime(string='Timestamp')
    state = fields.Selection([
        ('new', 'New'),
        ('processed', 'Processed'),
        ('error', 'Error')
    ], string='Status', default='new', required=True, copy=False)
    raw_data = fields.Text(string='Raw Data')
    
    hr_attendance_id = fields.Many2one('hr.attendance', string='Odoo Attendance Record', readonly=True)

    def _get_shift_times(self, employee, check_datetime_local, device_timezone):
        shift = employee.turno_id
        if not shift:
            return None, None
        
        # Obtenemos las horas correctas para ese día específico
        entrada_config, salida_config = shift.get_times_for_date(check_datetime_local.date())

        if not entrada_config or not salida_config:
            return None, None

        # Convertir de la base de datos (UTC) a la zona local del dispositivo
        entrada_naive = fields.Datetime.from_string(entrada_config)
        salida_naive = fields.Datetime.from_string(salida_config)
        
        shift_in_local_dt = pytz.utc.localize(entrada_naive).astimezone(device_timezone)
        shift_out_local_dt = pytz.utc.localize(salida_naive).astimezone(device_timezone)

        # Usar solo la hora y aplicarla a la fecha de la checada
        shift_in_time = shift_in_local_dt.time()
        shift_out_time = shift_out_local_dt.time()
        shift_date = check_datetime_local.date()
        
        shift_in_datetime_local = device_timezone.localize(datetime.combine(shift_date, shift_in_time))
        shift_out_datetime_local = device_timezone.localize(datetime.combine(shift_date, shift_out_time))

        # Manejo de cruce de medianoche (turno nocturno)
        if shift_out_time <= shift_in_time:
             shift_out_datetime_local += timedelta(days=1)
        
        return shift_in_datetime_local.astimezone(pytz.utc), shift_out_datetime_local.astimezone(pytz.utc)

    def _create_attendance(self, employee, check_in_utc, status_in):
        """Función auxiliar para crear un registro de hr.attendance."""
        Attendance = self.env['hr.attendance'].sudo()
        return Attendance.create({
            'employee_id': employee.id,
            'check_in': check_in_utc,
            'punctuality_status': status_in,
        })

    def _close_attendance(self, attendance_record, check_out_utc, status_out=None):
        """Función auxiliar para cerrar un registro de hr.attendance y opcionalmente actualizar el status."""
        vals = {'check_out': check_out_utc}
        if status_out:
            vals['punctuality_status'] = status_out
        attendance_record.write(vals)

    def process_logs(self):
        records_to_process = self.filtered(lambda l: l.state == 'new').sudo()
        
        Attendance = self.env['hr.attendance'].sudo()
        Employee = self.env['hr.employee'].sudo()
        Device = self.env['zkteco.device'].sudo()

        if not records_to_process:
            return
            
        UTC_TIMEZONE = pytz.utc
            
        for log in records_to_process:

            attendance_record = False
            device_serial = log.device_id
            if not device_serial:
                _logger.warning("El log Id: %s no tiene número de serie (Device ID). Log Marcado como error.", log.id)
                log.state = 'error'
                continue

            device = Device.search([('serial_number', '=', device_serial)], limit=1)

            if not device:
                _logger.warning("Dispositivo con S/N: %s No encontrado en Odoo. El Log ID: %s se marca como error.", device_serial, log.id)
                log.state = 'error'
                continue

            company_id = device.company_id.id
            company = device.company_id

            # Obtener zona horaria de la empresa (o usar por defecto si no está configurada)
            company_tz_name = company.timezone or FIXED_DEVICE_TIMEZONE_NAME
            try:
                DEVICE_TIMEZONE = pytz.timezone(company_tz_name)
            except pytz.UnknownTimeZoneError:
                _logger.error("Configuration Error: The timezone '%s' for company '%s' is invalid. Log set to 'error'.", company_tz_name, company.name)
                log.state = 'error'
                continue

            search_id = str(log.user_id)
            employee = Employee.search([
                ('biometric_id', '=', search_id),
                ('company_id', '=', company_id)    
            ], limit=1)
            
            if not employee:
                _logger.warning("Empleado NO ENCONTRADO con ID Biométrico: %s Y Compañía: %s (Device: %s). Log ID: %s marcado como error.", 
                                search_id, device.company_id.name, device_serial, log.id)
                log.state = 'error'
                continue

            try:
                naive_datetime = fields.Datetime.from_string(log.timestamp)
                
                # Convertir la fecha del dispositivo (en zona local) a UTC para comparación correcta
                device_datetime_local = DEVICE_TIMEZONE.localize(naive_datetime, is_dst=None)
                device_datetime_utc = device_datetime_local.astimezone(UTC_TIMEZONE)
                
                # Validar si la fecha tiene más de 30 minutos de diferencia
                now_utc = UTC_TIMEZONE.localize(datetime.utcnow())
                time_diff_seconds = abs((device_datetime_utc - now_utc).total_seconds())
                time_diff_minutes = time_diff_seconds / 60
                
                if time_diff_minutes > 10:  # Más de 10 minutos de diferencia
                    _logger.warning(
                        "⚠️ Fecha de checada inválida detectada para log %s (Employee: %s, Device: %s). "
                        "Fecha del dispositivo (local): %s, Diferencia: %.1f minutos. Usando hora actual.",
                        log.id, employee.name, device_serial, naive_datetime, time_diff_minutes
                    )
                    
                    # Usar hora actual en la zona horaria de la empresa
                    check_datetime_local = datetime.now(DEVICE_TIMEZONE)
                    _logger.info("✅ Usando hora actual de la empresa (%s): %s", company_tz_name, check_datetime_local)
                else:
                    # Fecha válida, procesar normalmente
                    check_datetime_local = device_datetime_local
                
                check_datetime_utc_dt = check_datetime_local.astimezone(UTC_TIMEZONE) 
                check_datetime_utc = fields.Datetime.to_string(check_datetime_utc_dt)
                
            except Exception as e:
                _logger.error("Error de conversión de fecha/hora para log %s: %s", log.id, str(e))
                log.state = 'error'
                continue

            last_attendance = employee.last_attendance_id.sudo()
            
            shift_in_utc_dt, shift_out_utc_dt = self._get_shift_times(employee, check_datetime_local, DEVICE_TIMEZONE)

            if not last_attendance or last_attendance.check_out:
                
                status = 'n/a'
                if shift_in_utc_dt:

                    max_on_time = shift_in_utc_dt + timedelta(minutes=TIME_OFFSET_MINUTES)
                    
                    if check_datetime_utc_dt <= max_on_time:
                        status = 'on_time'
                    else:
                        status = 'late'
                        
                attendance_record = self._create_attendance(employee, check_datetime_utc, status)
                _logger.info("CHECK-IN (Primera Checada) processed for %s at %s. Status: %s", employee.name, log.timestamp, status)

            else:
                self._close_attendance(last_attendance, check_datetime_utc) 

                is_end_of_shift = False
                if shift_out_utc_dt and check_datetime_utc_dt >= (shift_out_utc_dt - timedelta(minutes=10)):
                    is_end_of_shift = True
                
                if not is_end_of_shift: 
                    
                    previous_status = last_attendance.punctuality_status
                    
                    if previous_status in ('on_time', 'late', 'LunchE'): 
                        new_status = 'LunchS'
                    else: 
                        new_status = 'LunchE'

                    attendance_record = self._create_attendance(employee, check_datetime_utc, new_status)
                    _logger.info("CHECK-OUT y Nuevo CHECK-IN Intermedio processed for %s at %s. Status: %s", employee.name, log.timestamp, new_status)

                else:
                    check_in_end = check_datetime_utc_dt 
                    check_out_end = check_datetime_utc_dt + timedelta(seconds=SECOND_DIFFERENCE)
                    
                    attendance_record = self._create_attendance(employee, fields.Datetime.to_string(check_in_end), 'end')
                    self._close_attendance(attendance_record, fields.Datetime.to_string(check_out_end))
                    
                    _logger.info("CHECK-OUT y CHECK-IN/OUT (Fin de Turno) processed for %s at %s.", employee.name, log.timestamp)
            
            if attendance_record:
                log.write({
                    'state': 'processed',
                    'hr_attendance_id': attendance_record.id
                })
            else:
                raise Exception("Attendance record could not be created or found.")