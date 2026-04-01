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
RECOVERY_LOOKBACK_DAYS = 30
BACKLOG_RECENT_WINDOW_MINUTES = 10
BACKLOG_ON_TIME_WINDOW_HOURS = 4

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

    def _get_day_bounds_utc(self, target_date, device_timezone):
        day_start_local = device_timezone.localize(datetime.combine(target_date, time.min))
        day_end_local = device_timezone.localize(datetime.combine(target_date, time.max))
        return day_start_local.astimezone(pytz.utc), day_end_local.astimezone(pytz.utc)

    def _has_workday_shift(self, employee, target_date):
        shift = employee.turno_id
        if not shift:
            return False
        entrada_config, salida_config = shift.get_times_for_date(target_date)
        return bool(entrada_config and salida_config)

    def _get_day_attendance_context(self, employee, attendance_model, device_timezone, target_date):
        """Devuelve contexto de asistencia para una fecha específica del empleado."""
        day_start_utc, day_end_utc = self._get_day_bounds_utc(target_date, device_timezone)
        day_start_str = fields.Datetime.to_string(day_start_utc)
        day_end_str = fields.Datetime.to_string(day_end_utc)

        has_absence = bool(attendance_model.search([
            ('employee_id', '=', employee.id),
            ('punctuality_status', '=', 'absence'),
            ('check_in', '>=', day_start_str),
            ('check_in', '<=', day_end_str),
        ], limit=1))

        has_real_attendance = bool(attendance_model.search([
            ('employee_id', '=', employee.id),
            ('punctuality_status', '!=', 'absence'),
            ('check_in', '>=', day_start_str),
            ('check_in', '<=', day_end_str),
        ], limit=1))

        return {
            'is_workday': self._has_workday_shift(employee, target_date),
            'has_absence': has_absence,
            'has_real_attendance': has_real_attendance,
        }

    def _delete_absence_for_day(self, employee, attendance_model, device_timezone, target_date):
        day_start_utc, day_end_utc = self._get_day_bounds_utc(target_date, device_timezone)
        day_start_str = fields.Datetime.to_string(day_start_utc)
        day_end_str = fields.Datetime.to_string(day_end_utc)
        absence = attendance_model.search([
            ('employee_id', '=', employee.id),
            ('punctuality_status', '=', 'absence'),
            ('check_in', '>=', day_start_str),
            ('check_in', '<=', day_end_str),
        ], limit=1)
        if absence:
            absence.unlink()
            return True
        return False

    def _get_shift_in_local_for_date(self, employee, target_date, device_timezone):
        shift = employee.turno_id
        if not shift:
            return None

        entrada_config, salida_config = shift.get_times_for_date(target_date)
        if not entrada_config or not salida_config:
            return None

        entrada_naive = fields.Datetime.from_string(entrada_config)
        shift_timezone = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        entrada_local_dt = pytz.utc.localize(entrada_naive).astimezone(shift_timezone)
        shift_in_time = entrada_local_dt.time()

        # Aplicar la hora del turno en la zona del empleado para que "08:05" signifique
        # "08:05 local del empleado" sin importar desde dónde se configuró.
        company_tz_name = employee.company_id.timezone or FIXED_DEVICE_TIMEZONE_NAME
        try:
            employee_tz = pytz.timezone(company_tz_name)
        except pytz.UnknownTimeZoneError:
            employee_tz = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        return employee_tz.localize(datetime.combine(target_date, shift_in_time))

    def _device_backlog_mode_active(self, device_serial, now_utc, device_timezone):
        """
        Detecta si este dispositivo acaba de procesar checadas reubicadas a días anteriores
        en una ventana corta; se usa para evitar retardo falso en la primera checada de hoy.
        """
        cutoff_utc = now_utc - timedelta(minutes=BACKLOG_RECENT_WINDOW_MINUTES)
        today_local = now_utc.astimezone(device_timezone).date()
        today_start_utc, _ = self._get_day_bounds_utc(today_local, device_timezone)

        recent_logs = self.search([
            ('device_id', '=', device_serial),
            ('state', '=', 'processed'),
            ('create_date', '>=', fields.Datetime.to_string(cutoff_utc)),
            ('hr_attendance_id', '!=', False),
        ], order='id desc', limit=50)

        for log in recent_logs:
            attendance = log.hr_attendance_id
            if not attendance or not attendance.check_in:
                continue

            attendance_check_in = attendance.check_in
            if attendance_check_in.tzinfo is None:
                attendance_check_in = pytz.utc.localize(attendance_check_in)

            if attendance_check_in < today_start_utc:
                return True

        return False

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
        
        shift_timezone = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        shift_in_local_dt = pytz.utc.localize(entrada_naive).astimezone(shift_timezone)
        shift_out_local_dt = pytz.utc.localize(salida_naive).astimezone(shift_timezone)

        # Usar solo la hora y aplicarla a la fecha de la checada
        shift_in_time = shift_in_local_dt.time()
        shift_out_time = shift_out_local_dt.time()
        shift_date = check_datetime_local.date()

        # Aplicar la hora del turno en la zona del empleado para que "08:05" signifique
        # "08:05 local del empleado" sin importar desde dónde se configuró.
        company_tz_name = employee.company_id.timezone or FIXED_DEVICE_TIMEZONE_NAME
        try:
            employee_tz = pytz.timezone(company_tz_name)
        except pytz.UnknownTimeZoneError:
            employee_tz = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)

        shift_in_datetime_local = employee_tz.localize(datetime.combine(shift_date, shift_in_time))
        shift_out_datetime_local = employee_tz.localize(datetime.combine(shift_date, shift_out_time))

        # Manejo de cruce de medianoche (turno nocturno)
        if shift_out_time <= shift_in_time:
             shift_out_datetime_local += timedelta(days=1)
        
        return shift_in_datetime_local.astimezone(pytz.utc), shift_out_datetime_local.astimezone(pytz.utc)

    def _create_attendance(self, employee, check_in_utc, status_in):
        """Función auxiliar para crear un registro de hr.attendance."""
        Attendance = self.env['hr.attendance'].sudo().with_context(skip_attendance_sync=True)
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
        attendance_record.with_context(skip_attendance_sync=True).write(vals)

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

            is_historical = False

            try:
                naive_datetime = fields.Datetime.from_string(log.timestamp)
                
                # Convertir la fecha del dispositivo (en zona local) a UTC para comparación correcta
                device_datetime_local = DEVICE_TIMEZONE.localize(naive_datetime, is_dst=None)
                device_datetime_utc = device_datetime_local.astimezone(UTC_TIMEZONE)
                
                # Validar si la fecha tiene más de 10 minutos de diferencia
                now_utc = UTC_TIMEZONE.localize(datetime.utcnow())
                time_diff_seconds = abs((device_datetime_utc - now_utc).total_seconds())
                time_diff_minutes = time_diff_seconds / 60

                reported_date_local = device_datetime_local.date()
                today_local = now_utc.astimezone(DEVICE_TIMEZONE).date()

                # Regla principal: si la fecha del dispositivo es HOY (desfasado o exacto),
                # siempre usar la hora actual de la empresa para el registro.
                # Solo respetamos el timestamp original cuando la fecha es un día PASADO.
                if reported_date_local >= today_local:
                    # Hoy o futuro → siempre hora actual
                    if time_diff_minutes > 10:
                        if device_datetime_utc > now_utc:
                            _logger.warning(
                                "⚠️ Fecha FUTURA para log %s (Employee: %s, Device: %s). "
                                "Hora dispositivo: %s, Diferencia: %.1f min. Usando hora actual.",
                                log.id, employee.name, device_serial, naive_datetime, time_diff_minutes
                            )
                        else:
                            _logger.warning(
                                "⚠️ Reloj desfasado (mismo día) para log %s (Employee: %s, Device: %s). "
                                "Hora dispositivo: %s, Diferencia: %.1f min. Usando hora actual.",
                                log.id, employee.name, device_serial, naive_datetime, time_diff_minutes
                            )
                    check_datetime_local = datetime.now(DEVICE_TIMEZONE)
                    # Si había falta generada para hoy, eliminarla
                    reported_day_ctx = self._get_day_attendance_context(
                        employee, Attendance, DEVICE_TIMEZONE, reported_date_local
                    )
                    if reported_day_ctx['has_absence']:
                        self._delete_absence_for_day(employee, Attendance, DEVICE_TIMEZONE, reported_date_local)
                    _logger.info("✅ Usando hora actual (%s): %s", company_tz_name, check_datetime_local)

                else:
                    # Fecha PASADA — intentar recuperación histórica
                    days_in_past = (now_utc - device_datetime_utc).total_seconds() / 86400
                    if days_in_past > RECOVERY_LOOKBACK_DAYS:
                        # Fuera del rango histórico permitido — tratar como desfase
                        _logger.warning(
                            "⚠️ Fecha pasada mayor a %s días para log %s (Employee: %s, Device: %s). "
                            "Fecha dispositivo: %s, Días de diferencia: %.1f. Usando hora actual.",
                            RECOVERY_LOOKBACK_DAYS, log.id, employee.name, device_serial, naive_datetime, days_in_past
                        )
                        check_datetime_local = datetime.now(DEVICE_TIMEZONE)
                        _logger.info("✅ Usando hora actual (%s): %s", company_tz_name, check_datetime_local)
                    else:
                        # Dentro de los últimos días permitidos — checada histórica válida
                        original_date = device_datetime_local.date()
                        orig_day_start = DEVICE_TIMEZONE.localize(
                            datetime.combine(original_date, time.min)
                        ).astimezone(UTC_TIMEZONE)
                        orig_day_end = DEVICE_TIMEZONE.localize(
                            datetime.combine(original_date, time.max)
                        ).astimezone(UTC_TIMEZONE)
                        orig_start_str = fields.Datetime.to_string(orig_day_start)
                        orig_end_str = fields.Datetime.to_string(orig_day_end)

                        # Check 1: falta auto-generada para esa fecha
                        absence_on_orig_date = Attendance.search([
                            ('employee_id', '=', employee.id),
                            ('punctuality_status', '=', 'absence'),
                            ('check_in', '>=', orig_start_str),
                            ('check_in', '<=', orig_end_str),
                        ], limit=1)

                        # Check 2: asistencia real ABIERTA en esa fecha (2da+ checada del mismo día,
                        # creada en este mismo batch — nunca una asistencia ya cerrada/completa)
                        checkin_on_orig_date = Attendance.search([
                            ('employee_id', '=', employee.id),
                            ('punctuality_status', '!=', 'absence'),
                            ('check_in', '>=', orig_start_str),
                            ('check_in', '<=', orig_end_str),
                            ('check_out', '=', False),
                        ], limit=1)

                        if absence_on_orig_date:
                            _logger.info(
                                "📋 Checada histórica detectada para %s (Log %s). Fecha: %s — "
                                "falta auto-generada encontrada, eliminando y usando timestamp original.",
                                employee.name, log.id, original_date
                            )
                            absence_on_orig_date.unlink()
                            check_datetime_local = device_datetime_local
                            is_historical = True
                        elif checkin_on_orig_date:
                            _logger.info(
                                "📋 Checada histórica (2da+ del día) para %s (Log %s). Fecha: %s — "
                                "asistencia abierta encontrada, usando timestamp original.",
                                employee.name, log.id, original_date
                            )
                            check_datetime_local = device_datetime_local
                            is_historical = True
                        else:
                            # Sin falta ni asistencia abierta en esa fecha
                            reported_day_ctx = self._get_day_attendance_context(
                                employee, Attendance, DEVICE_TIMEZONE, original_date
                            )
                            if reported_day_ctx['is_workday'] and not reported_day_ctx['has_real_attendance']:
                                check_datetime_local = device_datetime_local
                                if reported_day_ctx['has_absence']:
                                    self._delete_absence_for_day(
                                        employee, Attendance, DEVICE_TIMEZONE, original_date
                                    )
                                is_historical = True
                                _logger.info(
                                    "📋 Checada histórica sin falta previa para %s (Log %s). "
                                    "Fecha: %s — usando timestamp original.",
                                    employee.name, log.id, original_date
                                )
                            else:
                                # Día no laborable o ya tiene asistencia cerrada — usar hora actual
                                _logger.warning(
                                    "⚠️ Fecha pasada sin contexto válido para log %s (Employee: %s, Device: %s). "
                                    "Fecha dispositivo: %s. Usando hora actual.",
                                    log.id, employee.name, device_serial, naive_datetime
                                )
                                check_datetime_local = datetime.now(DEVICE_TIMEZONE)
                                _logger.info("✅ Usando hora actual (%s): %s", company_tz_name, check_datetime_local)
                
                check_datetime_utc_dt = check_datetime_local.astimezone(UTC_TIMEZONE) 
                check_datetime_utc = fields.Datetime.to_string(check_datetime_utc_dt)
                
            except Exception as e:
                _logger.error("Error de conversión de fecha/hora para log %s: %s", log.id, str(e))
                log.state = 'error'
                continue

            last_attendance = employee.last_attendance_id.sudo()
            shift_in_utc_dt, shift_out_utc_dt = self._get_shift_times(employee, check_datetime_local, DEVICE_TIMEZONE)

            # Para checadas históricas, usar la última asistencia del mismo día histórico
            # (no la global, que podría ser del día actual y causaría cierres/aperturas incorrectos)
            if is_historical:
                check_date = check_datetime_local.date()
                hist_day_start = DEVICE_TIMEZONE.localize(
                    datetime.combine(check_date, time.min)
                ).astimezone(UTC_TIMEZONE)
                hist_day_end = DEVICE_TIMEZONE.localize(
                    datetime.combine(check_date, time.max)
                ).astimezone(UTC_TIMEZONE)
                last_attendance = Attendance.search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', fields.Datetime.to_string(hist_day_start)),
                    ('check_in', '<=', fields.Datetime.to_string(hist_day_end)),
                ], order='check_in desc', limit=1)

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