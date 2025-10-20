# -*- coding: utf-8 -*-

import pytz
import logging
from datetime import datetime, timedelta, time
from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

FIXED_DEVICE_TIMEZONE_NAME = 'America/Tijuana'
TIME_OFFSET_MINUTES = 5 # Tolerancia de 5 minutos para el retardo
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

    def _get_shift_times(self, employee, check_datetime_local):
        """
        Calcula la hora de entrada y salida del turno para la fecha dada
        en el huso horario local del dispositivo (o la zona de la checada).
        Retorna datetime.datetime localizados o None.
        """
        shift = employee.turno_id
        if not shift or not shift.hora_entrada or not shift.hora_salida:
            return None, None
        
        # 1. Preparación de Zonas Horarias
        try:
            FIXED_TIMEZONE = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        except pytz.UnknownTimeZoneError:
            _logger.error("Error de configuración: Zona horaria '%s' es inválida.", FIXED_DEVICE_TIMEZONE_NAME)
            return None, None

        entrada_naive = fields.Datetime.from_string(shift.hora_entrada)
        salida_naive = fields.Datetime.from_string(shift.hora_salida)
        
        # 2.2 Localizar a UTC y luego a FIXED_TIMEZONE
        shift_in_local_dt = pytz.utc.localize(entrada_naive).astimezone(FIXED_TIMEZONE)
        shift_out_local_dt = pytz.utc.localize(salida_naive).astimezone(FIXED_TIMEZONE)

        # El resto del código de la función permanece igual...
        shift_in_time = shift_in_local_dt.time()
        shift_out_time = shift_out_local_dt.time()

        # Combinar el time del turno con la date local de la checada
        shift_date = check_datetime_local.date()
        
        shift_in_datetime_local = FIXED_TIMEZONE.localize(datetime.combine(shift_date, shift_in_time))
        shift_out_datetime_local = FIXED_TIMEZONE.localize(datetime.combine(shift_date, shift_out_time))

        # Manejar turnos nocturnos: si la hora de salida es anterior a la de entrada,
        if shift_out_time <= shift_in_time:
             shift_out_datetime_local += timedelta(days=1)
        
        # Odoo requiere UTC para check_in/check_out
        shift_in_utc = shift_in_datetime_local.astimezone(pytz.utc)
        shift_out_utc = shift_out_datetime_local.astimezone(pytz.utc)
        
        return shift_in_utc, shift_out_utc


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

        if not records_to_process:
            return
            
        UTC_TIMEZONE = pytz.utc
        try:
            FIXED_TIMEZONE = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        except pytz.UnknownTimeZoneError:
            _logger.error("Configuration Error: The defined timezone '%s' is invalid. All logs set to 'error'.", FIXED_DEVICE_TIMEZONE_NAME)
            records_to_process.write({'state': 'error'})
            return
            
        # 1. PROCESAMIENTO DE CHECADAS
        for log in records_to_process:
            search_id = str(log.user_id)
            employee = Employee.search([('biometric_id', '=', search_id)], limit=1)

            if not employee:
                _logger.warning("Employee NOT FOUND in Odoo for Biometric ID: %s. Log marked as error.", search_id)
                log.state = 'error'
                continue

            # Obtener y Localizar la hora de la checada
            try:
                naive_datetime = fields.Datetime.from_string(log.timestamp) 
                check_datetime_local = FIXED_TIMEZONE.localize(naive_datetime, is_dst=None)
                # Mantener el objeto datetime localizado a UTC para comparaciones
                check_datetime_utc_dt = check_datetime_local.astimezone(UTC_TIMEZONE) 
                # Usar fields.Datetime.to_string() (o strftime) solo para el ORM de Odoo
                check_datetime_utc = fields.Datetime.to_string(check_datetime_utc_dt)
                
            except Exception as e:
                _logger.error("Error de conversión de fecha/hora para log %s: %s", log.id, str(e))
                log.state = 'error'
                continue

            last_attendance = employee.last_attendance_id.sudo()
            
            # Obtener horas del turno
            shift_in_utc_dt, shift_out_utc_dt = self._get_shift_times(employee, check_datetime_local)

            # Caso 1: Primera checada del día (No hay registro abierto)
            if not last_attendance or last_attendance.check_out:
                
                # --- Lógica de la PRIMERA CHECADA (A tiempo / Retardo) ---
                status = 'n/a'
                if shift_in_utc_dt:
                    # Hora máxima para llegar 'A tiempo' (Hora de entrada + 5 minutos de tolerancia)
                    max_on_time = shift_in_utc_dt + timedelta(minutes=TIME_OFFSET_MINUTES)
                    
                    if check_datetime_utc_dt <= max_on_time:
                        status = 'on_time'
                    else:
                        status = 'late'
                        
                attendance_record = self._create_attendance(employee, check_datetime_utc, status)
                _logger.info("CHECK-IN (Primera Checada) processed for %s at %s. Status: %s", employee.name, log.timestamp, status)

            # Caso 2: Checada Intermedia o Final (Hay registro abierto)
            else:
                # El registro abierto es last_attendance
                
                # CERRAR el registro anterior (check_out)
                self._close_attendance(last_attendance, check_datetime_utc) 
                
                # --- Lógica de Salida/Regreso o Fin de Turno ---
                
                # Si la checada es ANTES de la hora de fin de turno programada:
                # Es una checada intermedia (Salida de Planta o Regreso a Planta)
                # NOTA: Comparamos el datetime de la checada con el datetime de fin de turno.
                is_end_of_shift = False
                if shift_out_utc_dt and check_datetime_utc_dt >= shift_out_utc_dt:
                    is_end_of_shift = True
                
                if not is_end_of_shift: 
                    # Es una checada INTERMEDIA: Salida de Planta / Regreso a Planta
                    
                    # 1. Definir el status: 
                    # Usamos el status del registro que se acaba de cerrar (la checada anterior)
                    # Si el status anterior fue 'on_time' o 'late', la nueva checada es 'Salida de Planta'
                    # Si el status anterior fue 'LunchS', la nueva checada es 'Regreso a Planta'
                    
                    previous_status = last_attendance.punctuality_status
                    
                    if previous_status in ('on_time', 'late', 'LunchE'): # Lógica: Si vienes de trabajar, vas de 'Salida de Planta'
                        new_status = 'LunchS'
                    else: # Lógica: Si vienes de 'LunchS', vas de 'Regreso a Planta'
                        new_status = 'LunchE'

                    # 2. Abrir un NUEVO registro de CHECK-IN con la misma hora
                    attendance_record = self._create_attendance(employee, check_datetime_utc, new_status)
                    _logger.info("CHECK-OUT y Nuevo CHECK-IN Intermedio processed for %s at %s. Status: %s", employee.name, log.timestamp, new_status)

                else:
                    # Es FIN DE TURNO (Checada después o justo a la hora de salida)
                    
                    # 1. Cerrar el registro anterior con la etiqueta 'Fin de turno'
                    # (Ya se cerró con el check_out arriba, pero cambiamos la etiqueta del registro anterior)
                    last_attendance.write({'punctuality_status': 'end'})
                    
                    # 2. Abrir y cerrar un NUEVO registro con la misma hora + 1 segundo
                    # (Para que Odoo detecte el check-in y check-out)
                    check_in_end = check_datetime_utc_dt # La hora de la checada
                    check_out_end = check_datetime_utc_dt + timedelta(seconds=SECOND_DIFFERENCE)
                    
                    attendance_record = self._create_attendance(employee, fields.Datetime.to_string(check_in_end), 'end')
                    self._close_attendance(attendance_record, fields.Datetime.to_string(check_out_end))
                    
                    _logger.info("CHECK-OUT y CHECK-IN/OUT (Fin de Turno) processed for %s at %s.", employee.name, log.timestamp)
            
            # 3. Marcado del log como procesado
            if attendance_record:
                log.write({
                    'state': 'processed',
                    'hr_attendance_id': attendance_record.id
                })
            else:
                raise Exception("Attendance record could not be created or found.")