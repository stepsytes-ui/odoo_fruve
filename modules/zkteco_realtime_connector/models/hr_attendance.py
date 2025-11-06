from odoo import fields, models, api, _
from datetime import datetime, timedelta, time
import pytz
import logging

_logger = logging.getLogger(__name__)


FIXED_DEVICE_TIMEZONE_NAME = 'America/Tijuana'

NEW_LEAVE_STATUSES = [
    ('leave_unpaid', 'Permiso sin goce de sueldo'),
    ('leave_paid', 'Permiso con goce de sueldo'),
    ('leave_sickness', 'Incapacidad'),
    ('leave_vacation', 'Vacaciones'),
    ('leave_maternity', 'Maternidad'),
    ('leave_paternity', 'Paternidad'),
    ('leave_suspension', 'Suspensión'),
    ('leave_other', 'Ausencia Justificada (Otro)')
]

LEAVE_STATUS_KEYS = [key for key, label in NEW_LEAVE_STATUSES]

AUTO_CLOSE_DELAY_HOURS = 5 

class HrAttendance(models.Model):

    _inherit = 'hr.attendance'

    punctuality_status = fields.Selection([
        ('on_time','A Tiempo'),
        ('late','Retardo'),
        ('absence', 'Falta'),
        ('LunchS','Salida de Planta'),
        ('LunchE','Regreso a Planta'),
        ('end','Fin de turno'),
        ('n/a','No aplica'),
    ] + NEW_LEAVE_STATUSES, string='Estatus de Puntualidad', default='n/a')

    check_in_time_only = fields.Char(
            string='Hora de Checada',
            compute='_compute_check_in_time_only',
            store=False
        )
    
    check_out_time_only = fields.Char(
            string=' ',
            compute='_compute_check_out_time_only',
            store=False
        )
    
    biometric_id = fields.Char(
        string='Número de Empleado',
        related='employee_id.biometric_id',
        store=True, # Importante para poder buscar y filtrar eficientemente
        readonly=True
    )

    def _compute_check_in_time_only(self):
        user_tz = self.env.user.tz or pytz.utc
        local_tz = pytz.timezone(user_tz)
        
        for record in self:
            if record.check_in:
                utc_datetime = pytz.utc.localize(record.check_in)
                local_datetime = utc_datetime.astimezone(local_tz)

                record.check_in_time_only = local_datetime.strftime("%d/%m/%Y, %H:%M:%S")
            else:
                    record.check_in_time_only = False

    def _compute_check_out_time_only(self):
        user_tz = self.env.user.tz or pytz.utc
        local_tz = pytz.timezone(user_tz)
        
        for record in self:
            if record.check_in:
                utc_datetime = pytz.utc.localize(record.check_in)
                local_datetime = utc_datetime.astimezone(local_tz)

                record.check_out_time_only = local_datetime.strftime("%d/%m/%Y, %H:%M:%S")
            else:
                    record.check_out_time_only = False

    @api.model
    def _cron_generate_absences(self):
        _logger.info("Iniciando CRON para generar faltas...")
        
        try:
            COMPANY_TZ = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        except pytz.UnknownTimeZoneError:
            _logger.error(f"Error de Cron: Zona horaria '{FIXED_DEVICE_TIMEZONE_NAME}' es inválida.")
            return

        today_local = datetime.now(COMPANY_TZ).date()
        check_date = today_local - timedelta(days=1)
        
        day_mapping = {
            0: 'work_monday',
            1: 'work_tuesday',
            2: 'work_wednesday',
            3: 'work_thursday',
            4: 'work_friday',
            5: 'work_saturday',
            6: 'work_sunday',
        }
        day_of_week_int = check_date.weekday()
        field_to_check = day_mapping.get(day_of_week_int)

        if not field_to_check:
            _logger.warning(f"Error de Cron: No se pudo determinar el día de la semana para {check_date}.")
            return

        Employee = self.env['hr.employee']
        employees_to_check = Employee.search([
            ('employee_status', '=', 'active'),
            ('turno_id', '!=', False),
            (f'turno_id.{field_to_check}', '=', True)
        ])

        if not employees_to_check:
            _logger.info(f"Cron Faltas: No se encontraron empleados programados para trabajar en {check_date}.")
            return

        start_of_day_local = COMPANY_TZ.localize(datetime.combine(check_date, time.min))
        end_of_day_local = COMPANY_TZ.localize(datetime.combine(check_date, time.max))

        start_of_day_utc = start_of_day_local.astimezone(pytz.utc)
        end_of_day_utc = end_of_day_local.astimezone(pytz.utc)
        
        start_utc_str = fields.Datetime.to_string(start_of_day_utc)
        end_utc_str = fields.Datetime.to_string(end_of_day_utc)

        _logger.info(f"Revisando faltas para {len(employees_to_check)} empleados en el rango UTC: {start_utc_str} a {end_utc_str}")
        Attendance = self.env['hr.attendance']
        Leave = self.env['hr.leave'].sudo()

        leave_status_map = {
            'Permiso sin goce de sueldo': 'leave_unpaid',
            'Permiso con goce de sueldo': 'leave_paid',
            'Incapacidad': 'leave_sickness',
            'Vacaciones': 'leave_vacation',
            'Maternidad': 'leave_maternity',
            'Paternidad': 'leave_paternity',
            'Suspension': 'leave_suspension',
        }

        for employee in employees_to_check:
            attendance_exists = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_utc_str),
                ('check_in', '<=', end_utc_str),
                ('punctuality_status', 'in', ['on_time', 'late'])
            ], limit=1)

            if not attendance_exists:

                approved_leave = Leave.search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'validate'),
                    ('date_from', '<=', end_utc_str), 
                    ('date_to', '>=', start_utc_str)   
                ], limit=1)
                
                check_out_time = start_of_day_utc + timedelta(seconds=1)
                
                if approved_leave:
                    leave_name = approved_leave.holiday_status_id.name
                    new_status = leave_status_map.get(leave_name, 'leave_other')

                    _logger.info(f"Generando AUSENCIA JUSTIFICADA ({new_status}) para {employee.name} (Permiso: {leave_name}) en {check_date}")
                    
                    Attendance.create({
                        'employee_id': employee.id,
                        'check_in': start_utc_str,
                        'check_out': fields.Datetime.to_string(check_out_time),
                        'punctuality_status': new_status,
                    })
                else:
                    _logger.info(f"Generando FALTA para {employee.name} (ID: {employee.biometric_id}) en {check_date}")
                    
                    Attendance.create({
                        'employee_id': employee.id,
                        'check_in': start_utc_str,
                        'check_out': fields.Datetime.to_string(check_out_time),
                        'punctuality_status': 'absence',
                    })

    @api.model
    def get_attendance_dashboard_stats(self, start_date=None, end_date=None):
        user_tz_name = self.env.user.tz or 'UTC'
        try:
            user_tz = pytz.timezone(user_tz_name)
        except pytz.UnknownTimeZoneError:
            user_tz = pytz.utc

        # Convertir fechas desde el frontend (formato YYYY-MM-DD)
        if start_date and end_date:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            today_local = datetime.now(user_tz).date()
            start_date_obj = today_local
            end_date_obj = today_local

        # Definir rangos de tiempo (inicio del primer día y fin del último día)
        start_of_day_local = user_tz.localize(datetime.combine(start_date_obj, time.min))
        end_of_day_local = user_tz.localize(datetime.combine(end_date_obj, time.max))

        start_utc = start_of_day_local.astimezone(pytz.utc)
        end_utc = end_of_day_local.astimezone(pytz.utc)

        start_utc_str = fields.Datetime.to_string(start_utc)
        end_utc_str = fields.Datetime.to_string(end_utc)

        # Dominios base y específicos
        base_domain = [('check_in', '>=', start_utc_str), ('check_in', '<=', end_utc_str)]
        present_domain = base_domain + [('punctuality_status', 'in', ['on_time', 'late'])]
        excused_domain = base_domain + [('punctuality_status', 'in', LEAVE_STATUS_KEYS)]
        unexcused_domain = base_domain + [('punctuality_status', '=', 'absence')]

        present_employees = self.search_read(present_domain, ['employee_id'])
        excused_employees = self.search_read(excused_domain, ['employee_id'])
        unexcused_employees = self.search_read(unexcused_domain, ['employee_id'])

        present_count = len(set(rec['employee_id'][0] for rec in present_employees if rec['employee_id']))
        excused_count = len(set(rec['employee_id'][0] for rec in excused_employees if rec['employee_id']))
        unexcused_count = len(set(rec['employee_id'][0] for rec in unexcused_employees if rec['employee_id']))

        return {
            'present_count': present_count,
            'excused_count': excused_count,
            'unexcused_count': unexcused_count,
        }
    
    @api.model
    def _get_shift_out_for_check_in(self, employee, check_in_dt_utc):
        """
        Calcula la hora de salida del turno para una hora de entrada específica.
        Reutiliza la lógica de turno (día y hora) basada en la fecha de check-in.
        """
        if not employee.turno_id:
            return None
            
        try:
            COMPANY_TZ = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        except pytz.UnknownTimeZoneError:
            _logger.error(f"Error: Zona horaria '{FIXED_DEVICE_TIMEZONE_NAME}' es inválida.")
            return None

        # 1. Convertir check_in_dt_utc a la zona horaria local de la compañía/dispositivo
        check_in_local_dt = check_in_dt_utc.astimezone(COMPANY_TZ)
        check_date = check_in_local_dt.date()
        
        # 2. Obtener los tiempos de turno (esto es simplificado, solo usa la hora)
        shift = employee.turno_id
        if not shift or not shift.hora_entrada or not shift.hora_salida:
            return None

        # 3. Reutilizar lógica de turno de ZkTecoAttendanceLog (ajustada)
        entrada_naive = fields.Datetime.from_string(shift.hora_entrada)
        salida_naive = fields.Datetime.from_string(shift.hora_salida)
        
        shift_out_local_dt = pytz.utc.localize(salida_naive).astimezone(COMPANY_TZ)
        shift_out_time = shift_out_local_dt.time()
        
        # Combinar la fecha del check-in con la hora de salida del turno
        shift_out_datetime_local = COMPANY_TZ.localize(datetime.combine(check_date, shift_out_time))
        
        # Manejo de turnos nocturnos
        entrada_local_dt = pytz.utc.localize(entrada_naive).astimezone(COMPANY_TZ)
        shift_in_time = entrada_local_dt.time()
        if shift_out_time <= shift_in_time:
            shift_out_datetime_local += timedelta(days=1)
            
        # 4. Convertir la hora de salida calculada a UTC
        shift_out_utc = shift_out_datetime_local.astimezone(pytz.utc)
        return shift_out_utc


    @api.model
    def _cron_auto_close_open_attendances(self):
        _logger.info("Iniciando CRON para cerrar asistencias abiertas (olvido de salida)...")

        now_utc = pytz.utc.localize(datetime.now())
        
        # 1. Buscar asistencias abiertas (check_out = False)
        open_attendances = self.search([
            ('check_out', '=', False),
            ('employee_id.employee_status', '=', 'active'),
            ('employee_id.turno_id', '!=', False)
        ])

        if not open_attendances:
            _logger.info("CRON Cierre: No se encontraron asistencias abiertas elegibles.")
            return

        attendances_to_close = self.env['hr.attendance']
        
        for attendance in open_attendances:
            employee = attendance.employee_id
            check_in_dt_utc = pytz.utc.localize(attendance.check_in)
            
            # 2. Obtener la hora de salida (check_out) programada para el día del check-in
            shift_out_dt_utc = self._get_shift_out_for_check_in(employee, check_in_dt_utc)

            if shift_out_dt_utc:
                # 3. Calcular la hora límite: Fin de turno + 5 horas de gracia
                close_limit_dt = shift_out_dt_utc + timedelta(hours=AUTO_CLOSE_DELAY_HOURS)
                
                # 4. Comprobar si ya se pasó el límite
                if now_utc >= close_limit_dt:
                    attendances_to_close += attendance

        if attendances_to_close:
            _logger.info(f"CRON Cierre: Cerrando {len(attendances_to_close)} asistencias abiertas.")
            for attendance in attendances_to_close:
                check_out_time = attendance.check_in + timedelta(minutes=1) 
                attendance.write({
                    'check_out': fields.Datetime.to_string(check_out_time), 
                })
                _logger.info(f"Cerrada asistencia de {attendance.employee_id.name}. Check-in: {fields.Datetime.to_string(attendance.check_in)}. Check-out: {fields.Datetime.to_string(check_out_time)}")
        else:
            _logger.info("CRON Cierre: No hay asistencias que necesiten ser cerradas automáticamente.")
