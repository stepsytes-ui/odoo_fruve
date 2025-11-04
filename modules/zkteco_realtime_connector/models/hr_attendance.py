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

    def _compute_check_in_time_only(self):
        user_tz = self.env.user.tz or pytz.utc
        local_tz = pytz.timezone(user_tz)
        
        for record in self:
            if record.check_in:
                # 1. Localizar el datetime UTC (check_in) a la zona horaria del usuario
                utc_datetime = pytz.utc.localize(record.check_in)
                local_datetime = utc_datetime.astimezone(local_tz)
                
                # 2. Formatear para mostrar solo la hora (HH:MM)
                record.check_in_time_only = local_datetime.strftime("%H:%M:%S")
            else:
                    record.check_in_time_only = False

    @api.model
    def _cron_generate_absences(self):
        _logger.info("Iniciando CRON para generar faltas...")
        
        try:
            COMPANY_TZ = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        except pytz.UnknownTimeZoneError:
            _logger.error(f"Error de Cron: Zona horaria '{FIXED_DEVICE_TIMEZONE_NAME}' es inválida.")
            return

        # 1. Definir el día que vamos a revisar (AYER)
        # Usamos la fecha "actual" en la zona horaria de la compañía
        today_local = datetime.now(COMPANY_TZ).date()
        check_date = today_local - timedelta(days=1)
        
        # 2. Mapeo de día de la semana (0=Lunes, 6=Domingo) a los campos del turno
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

        # 3. Buscar todos los empleados activos que DEBÍAN trabajar ayer
        Employee = self.env['hr.employee']
        employees_to_check = Employee.search([
            ('employee_status', '=', 'active'),
            ('turno_id', '!=', False),
            (f'turno_id.{field_to_check}', '=', True) # Filtra por el día de la semana
        ])

        if not employees_to_check:
            _logger.info(f"Cron Faltas: No se encontraron empleados programados para trabajar en {check_date}.")
            return

        # 4. Definir el rango de tiempo (todo el día de AYER) en UTC
        # Inicio del día (00:00:00) en la zona local
        start_of_day_local = COMPANY_TZ.localize(datetime.combine(check_date, time.min))
        # Fin del día (23:59:59) en la zona local
        end_of_day_local = COMPANY_TZ.localize(datetime.combine(check_date, time.max))

        # Convertir a UTC para la base de datos
        start_of_day_utc = start_of_day_local.astimezone(pytz.utc)
        end_of_day_utc = end_of_day_local.astimezone(pytz.utc)
        
        start_utc_str = fields.Datetime.to_string(start_of_day_utc)
        end_utc_str = fields.Datetime.to_string(end_of_day_utc)

        _logger.info(f"Revisando faltas para {len(employees_to_check)} empleados en el rango UTC: {start_utc_str} a {end_utc_str}")

        # 5. Iterar y verificar
        Attendance = self.env['hr.attendance']

        # Accedemos al modelo hr.leave (Time Off)
        Leave = self.env['hr.leave'].sudo()

        leave_status_map = {
            'Permiso sin goce de sueldo': 'leave_unpaid',
            'Permiso con goce de sueldo': 'leave_paid',
            'Incapacidad': 'leave_sickness',
            'Vacaciones': 'leave_vacation',
            'Maternidad': 'leave_maternity',
            'Paternidad': 'leave_paternity',
            'Suspension': 'leave_suspension',
            # Nota: 'Permison' se corrigió a 'Permiso'
        }

        for employee in employees_to_check:
            # Buscar una asistencia de ENTRADA (on_time o late) para ese empleado en ese día
            attendance_exists = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_utc_str),
                ('check_in', '<=', end_utc_str),
                ('punctuality_status', 'in', ['on_time', 'late'])
            ], limit=1)

            # 6. Si NO existe, crear el registro de FALTA
            if not attendance_exists:

                approved_leave = Leave.search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'validate'),          # Solo permisos aprobados
                    ('date_from', '<=', end_utc_str),   # Que el permiso haya iniciado antes de que termine el día
                    ('date_to', '>=', start_utc_str)    # Y que el permiso termine después de que inicie el día
                ], limit=1)
                
                # Creamos un registro de "Falta" al inicio del día.
                # Dura 1 segundo para que no compute horas trabajadas.
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
                    # 6c. No se encontró permiso. Generar FALTA (lógica original).
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
