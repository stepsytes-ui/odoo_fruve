from odoo import fields, models, api, _
from datetime import datetime, timedelta, time
import pytz
import logging

_logger = logging.getLogger(__name__)


FIXED_DEVICE_TIMEZONE_NAME = 'America/Tijuana'

NEW_LEAVE_STATUSES = [
    ('leave_paid', 'Permiso pagado'),
    ('leave_vacation', 'Vacaciones'),
    ('leave_maternity', 'Maternidad'),
    ('leave_paternity', 'Paternidad'),
    ('leave_sickness', 'Incapacidad'),
    ('leave_suspension', 'Suspensión'),
    ('leave_unpaid', 'Permiso no pagado'),
    ('leave_payday', 'Permiso día pagado'),
    ('leave_birthday', 'Permiso por cumpleaños'),
    ('leave_delay_pass_paid', 'Permiso retardo'),
    ('leave_marriage', 'Permiso por matrimonio'),
    ('leave_no_payday', 'Permiso día no pagado'),
    ('leave_other', 'Ausencia Justificada (Otro)'),
    ('leave_partial_paid', 'Permiso parcial pagado'),
    ('leave_partial_unpaid', 'Permiso parcial no pagado'),
]

LEAVE_STATUS_KEYS = [key for key, label in NEW_LEAVE_STATUSES]

AUTO_CLOSE_DELAY_HOURS = 5 

class HrAttendance(models.Model):

    _inherit = 'hr.attendance'

    punctuality_status = fields.Selection([
        ('late','Retardo'),
        ('absence', 'Falta'),
        ('on_time','A Tiempo'),
        ('end','Fin de turno'),
        ('overtime', 'Tiempo Extra'),
        ('LunchS','Salida de Planta'),
        ('LunchE','Regreso a Planta'),
        ('n/a','Checada desde Quiosco'),
        ('forgot_checkout', 'Olvido Checar Salida'),
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
        store=True,
        readonly=True
    )

    biometric_id_display = fields.Integer(
        string='No. Empleado',
        compute='_compute_biometric_id_display',
        store=True,
        readonly=True,
        aggregator=None,
        help='Campo numérico para ordenamiento sin comas'
    )

    turno_id = fields.Many2one(
        comodel_name='shift.management',
        string='Turno Asignado',
        related='employee_id.turno_id',
        store=True, 
        readonly=True
    )
    @api.depends('biometric_id')
    def _compute_biometric_id_display(self):
        """Mostrar biometric_id como entero para ordenamiento numérico"""
        for record in self:
            if record.biometric_id:
                try:
                    # Remover espacios y comas, convertir a entero
                    clean_id = record.biometric_id.replace(' ', '').replace(',', '')
                    record.biometric_id_display = int(clean_id)
                except (ValueError, AttributeError):
                    record.biometric_id_display = 0
            else:
                record.biometric_id_display = 0

    def _compute_check_in_time_only(self):
        for record in self:
            if record.check_in:
                # Usar la zona horaria de la empresa del empleado
                company_tz_name = record.employee_id.company_id.timezone or FIXED_DEVICE_TIMEZONE_NAME
                try:
                    local_tz = pytz.timezone(company_tz_name)
                except pytz.UnknownTimeZoneError:
                    local_tz = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
                
                utc_datetime = pytz.utc.localize(record.check_in)
                local_datetime = utc_datetime.astimezone(local_tz)

                record.check_in_time_only = local_datetime.strftime("%d/%m/%Y, %H:%M:%S")
            else:
                    record.check_in_time_only = False

    def _compute_check_out_time_only(self):
        for record in self:
            if record.check_out:
                # Usar la zona horaria de la empresa del empleado
                company_tz_name = record.employee_id.company_id.timezone or FIXED_DEVICE_TIMEZONE_NAME
                try:
                    local_tz = pytz.timezone(company_tz_name)
                except pytz.UnknownTimeZoneError:
                    local_tz = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
                
                utc_datetime = pytz.utc.localize(record.check_out)
                local_datetime = utc_datetime.astimezone(local_tz)

                record.check_out_time_only = local_datetime.strftime("%d/%m/%Y, %H:%M:%S")
            else:
                    record.check_out_time_only = False

    @api.model
    def _cron_generate_absences(self):
        """
        Se ejecuta a las 10pm de cada día.
        Genera faltas para empleados sin check_in en el día actual.
        Excluye: turno Seguridad (faltas manuales) y turno ESPECIAL (siempre tienen asistencia).
        """
        try:
            COMPANY_TZ = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        except pytz.UnknownTimeZoneError:
            _logger.error(f"Error de Cron: Zona horaria '{FIXED_DEVICE_TIMEZONE_NAME}' es inválida.")
            return

        # Usar el día ACTUAL (no el anterior)
        today_local = datetime.now(COMPANY_TZ).date()
        _logger.info(f"[CRON FALTAS] Iniciando generación de faltas para el día: {today_local}")
        
        day_mapping = {
            0: 'work_monday',
            1: 'work_tuesday',
            2: 'work_wednesday',
            3: 'work_thursday',
            4: 'work_friday',
            5: 'work_saturday',
            6: 'work_sunday',
        }
        day_of_week_int = today_local.weekday()
        field_to_check = day_mapping.get(day_of_week_int)

        # Verificar si es día festivo global (aplica a toda la empresa)
        CalendarLeaves = self.env['resource.calendar.leaves']
        start_of_day_local = COMPANY_TZ.localize(datetime.combine(today_local, time.min))
        end_of_day_local = COMPANY_TZ.localize(datetime.combine(today_local, time.max))
        
        start_of_day_utc = start_of_day_local.astimezone(pytz.utc)
        end_of_day_utc = end_of_day_local.astimezone(pytz.utc)
        
        # Buscar días festivos globales (sin resource_id = todos los empleados)
        public_holiday = CalendarLeaves.search([
            ('resource_id', '=', False),  # Festivo global
            ('date_from', '<=', fields.Datetime.to_string(end_of_day_utc)),
            ('date_to', '>=', fields.Datetime.to_string(start_of_day_utc))
        ], limit=1)
        
        if public_holiday:
            _logger.info(f"[CRON FALTAS] ⚠️ Hoy es día festivo: {public_holiday.name}. No se generarán faltas.")
            return
        
        Employee = self.env['hr.employee']
        # Excluir turnos Seguridad y ESPECIAL
        # Solo empleados activos (no inactivos ni en proceso de finiquito)
        employees_to_check = Employee.search([
            ('employee_status', '=', 'active'),
            ('turno_id', '!=', False),
            (f'turno_id.{field_to_check}', '=', True),  # Solo días laborales
            ('turno_id.turno_name', 'not in', ['Seguridad', 'ESPECIAL'])  # Excluir estos turnos
        ])

        _logger.info(f"[CRON FALTAS] Empleados a verificar: {len(employees_to_check)}")

        # Rango UTC ya calculado arriba, crear strings
        start_utc_str = fields.Datetime.to_string(start_of_day_utc)
        end_utc_str = fields.Datetime.to_string(end_of_day_utc)
        
        # check_out será 1 segundo después del check_in
        check_out_time_utc = start_of_day_utc + timedelta(seconds=1)
        check_out_str = fields.Datetime.to_string(check_out_time_utc)

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

        faltas_generadas = 0
        permisos_generados = 0

        for employee in employees_to_check:
            # Verificar si ya tiene algún check_in en el día
            attendance_exists = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_utc_str),
                ('check_in', '<=', end_utc_str)
            ], limit=1)

            if not attendance_exists:
                # Verificar si tiene un permiso aprobado
                approved_leave = Leave.search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'validate'),
                    ('date_from', '<=', end_utc_str), 
                    ('date_to', '>=', start_utc_str)   
                ], limit=1)
                
                if approved_leave:
                    # Crear registro con el tipo de permiso
                    leave_name = approved_leave.holiday_status_id.name
                    new_status = leave_status_map.get(leave_name, 'leave_other')
                    
                    Attendance.create({
                        'employee_id': employee.id,
                        'check_in': start_utc_str,
                        'check_out': check_out_str,
                        'punctuality_status': new_status,
                    })
                    permisos_generados += 1
                    _logger.info(f"[CRON FALTAS] ✅ Permiso registrado para {employee.name}: {leave_name}")
                else:
                    # Crear registro de falta
                    new_attendance = Attendance.create({
                        'employee_id': employee.id,
                        'check_in': start_utc_str,
                        'check_out': check_out_str,
                        'punctuality_status': 'absence',
                    })
                    faltas_generadas += 1
                    _logger.warning(f"[CRON FALTAS] ⚠️ Falta registrada para {employee.name}")

                    # Verificar si es la cuarta falta y enviar alerta
                    self._check_and_alert_four_absences(employee, new_attendance)
        
        _logger.info(f"[CRON FALTAS] ✅ Finalizado. Faltas: {faltas_generadas}, Permisos: {permisos_generados}")

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

        excused_employees = self.search_read(excused_domain, ['employee_id'])

        # Contar directamente los registros, sin usar set()
        present_count = self.search_count(present_domain)
        excused_count = len(set(rec['employee_id'][0] for rec in excused_employees if rec['employee_id']))
        unexcused_count = self.search_count(unexcused_domain)

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
        
        Args:
            employee: hr.employee record
            check_in_dt_utc: datetime en UTC (con timezone aware)
        """
        if not employee.turno_id:
            return None
            
        try:
            COMPANY_TZ = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        except pytz.UnknownTimeZoneError:
            _logger.error(f"Error: Zona horaria '{FIXED_DEVICE_TIMEZONE_NAME}' es inválida.")
            return None

        try:
            # 1. Asegurar que check_in_dt_utc es timezone-aware (debe ser UTC)
            if check_in_dt_utc.tzinfo is None:
                check_in_dt_utc = pytz.utc.localize(check_in_dt_utc)
            
            # Convertir a zona horaria local
            check_in_local_dt = check_in_dt_utc.astimezone(COMPANY_TZ)
            check_date = check_in_local_dt.date()
            
            # 2. Obtener los tiempos de turno
            shift = employee.turno_id
            if not shift or not shift.hora_entrada or not shift.hora_salida:
                return None

            # 3. Parsear las horas del turno (asumen que son strings en formato Odoo)
            try:
                entrada_dt = fields.Datetime.from_string(shift.hora_entrada)
                salida_dt = fields.Datetime.from_string(shift.hora_salida)
            except Exception as e:
                _logger.error(f"Error parseando horas de turno para {employee.name}: {e}")
                return None
            
            # Asegurar que son timezone-aware
            if entrada_dt.tzinfo is None:
                entrada_dt = pytz.utc.localize(entrada_dt)
            if salida_dt.tzinfo is None:
                salida_dt = pytz.utc.localize(salida_dt)
            
            # Convertir a zona local para extraer la hora
            entrada_local_dt = entrada_dt.astimezone(COMPANY_TZ)
            salida_local_dt = salida_dt.astimezone(COMPANY_TZ)
            
            shift_in_time = entrada_local_dt.time()
            shift_out_time = salida_local_dt.time()
            
            # Combinar la fecha del check-in con la hora de salida del turno
            shift_out_datetime_local = COMPANY_TZ.localize(datetime.combine(check_date, shift_out_time))
            
            # Manejo de turnos nocturnos (si salida es antes de entrada en la misma fecha)
            if shift_out_time <= shift_in_time:
                shift_out_datetime_local += timedelta(days=1)
                
            # 4. Convertir la hora de salida calculada a UTC
            shift_out_utc = shift_out_datetime_local.astimezone(pytz.utc)
            return shift_out_utc
            
        except Exception as e:
            _logger.error(f"Error en _get_shift_out_for_check_in para {employee.name}: {e}")
            return None


    @api.model
    def _cron_auto_close_open_attendances(self):
        """
        Cierra automáticamente las asistencias abiertas después de AUTO_CLOSE_DELAY_HOURS
        desde la hora de salida del turno.
        """
        try:
            now_utc = pytz.utc.localize(datetime.utcnow())
            _logger.info(f"[CRON AUTO-CLOSE] Iniciando búsqueda de asistencias abiertas. Hora actual UTC: {now_utc}")
            
            # 1. Buscar asistencias abiertas (check_out = False)
            open_attendances = self.search([
                ('check_out', '=', False),
                ('employee_id.employee_status', '=', 'active'),
                ('employee_id.turno_id', '!=', False)
            ])
            
            _logger.info(f"[CRON AUTO-CLOSE] Encontradas {len(open_attendances)} asistencias abiertas")
            
            attendances_to_close = []
            
            for attendance in open_attendances:
                try:
                    employee = attendance.employee_id
                    
                    # Asegurar que check_in es timezone-aware
                    if attendance.check_in.tzinfo is None:
                        check_in_dt_utc = pytz.utc.localize(attendance.check_in)
                    else:
                        check_in_dt_utc = attendance.check_in
                    
                    _logger.debug(f"[CRON AUTO-CLOSE] Procesando: {employee.name} - Check-in: {check_in_dt_utc}")
                    
                    shift_out_dt_utc = self._get_shift_out_for_check_in(employee, check_in_dt_utc)

                    if shift_out_dt_utc:
                        close_limit_dt = shift_out_dt_utc + timedelta(hours=AUTO_CLOSE_DELAY_HOURS)
                        time_until_close = close_limit_dt - now_utc
                        
                        _logger.debug(f"[CRON AUTO-CLOSE] {employee.name} - Salida: {shift_out_dt_utc}, Límite: {close_limit_dt}, Faltan: {time_until_close}")
                        
                        if now_utc >= close_limit_dt:
                            _logger.warning(f"[CRON AUTO-CLOSE] ⚠️ Cerrando asistencia para {employee.name} - Check-in: {check_in_dt_utc}")
                            attendances_to_close.append(attendance)
                    else:
                        _logger.warning(f"[CRON AUTO-CLOSE] No se pudo calcular hora de salida para {employee.name}")
                        
                except Exception as e:
                    _logger.error(f"[CRON AUTO-CLOSE] Error procesando asistencia {attendance.id}: {e}", exc_info=True)
                    continue

            # Cerrar las asistencias que ya pasaron el límite
            if attendances_to_close:
                _logger.info(f"[CRON AUTO-CLOSE] Cerrando {len(attendances_to_close)} asistencias")
                
                for attendance in attendances_to_close:
                    try:
                        # La hora de salida debe ser después de entrada, pero con un delay pequeño
                        if attendance.check_in.tzinfo is None:
                            check_in_dt = pytz.utc.localize(attendance.check_in)
                        else:
                            check_in_dt = attendance.check_in
                            
                        check_out_time = check_in_dt + timedelta(minutes=1)
                        
                        attendance.write({
                            'check_out': fields.Datetime.to_string(check_out_time),
                        })
                        _logger.info(f"[CRON AUTO-CLOSE] ✅ Cerrada asistencia: {attendance.employee_id.name}")
                        
                    except Exception as e:
                        _logger.error(f"[CRON AUTO-CLOSE] Error al cerrar asistencia {attendance.id}: {e}", exc_info=True)
                        continue
            else:
                _logger.info("[CRON AUTO-CLOSE] No hay asistencias para cerrar en este momento")
                
        except Exception as e:
            _logger.error(f"[CRON AUTO-CLOSE] Error crítico en el cron: {e}", exc_info=True)

    def _check_and_alert_four_absences(self, employee, new_attendance):
            """Verifica si el empleado tiene 4 faltas no justificadas y notifica al grupo de RRHH de su empresa."""
            
            # Dominio para contar solo las faltas (absence)
            absence_count = self.search_count([
                ('employee_id', '=', employee.id),
                ('punctuality_status', '=', 'absence')
            ])
            
            if absence_count == 4:
                        hr_group = self.env.ref('zkteco_realtime_connector.group_hr_manager_custom', raise_if_not_found=False)

                        if not hr_group:
                            _logger.warning("No se encontró el grupo de Recursos Humanos.")
                            return

                        # Obtener la empresa del empleado
                        employee_company = employee.company_id
                        if not employee_company:
                            _logger.warning(f"El empleado {employee.name} no tiene empresa asignada. No se enviará notificación.")
                            return

                        # Filtrar usuarios de RH que pertenecen a la misma empresa del empleado
                        hr_users = [user for user in hr_group.users if employee_company in user.company_ids]
                        
                        if not hr_users:
                            _logger.warning(f"No se encontraron usuarios de RRHH para la empresa {employee_company.name}.")
                            return

                        recipient_partner_ids = [user.partner_id.id for user in hr_users if user.partner_id and user.partner_id.email]
                        
                        if not recipient_partner_ids:
                            _logger.warning(f"Los usuarios de RRHH de la empresa {employee_company.name} no tienen correo electrónico configurado.")
                            return
                        
                        recipient_user_ids = [user.id for user in hr_users]
                        # Convertir los IDs a un formato para 'recipient_ids' [(4, id), (4, id), ...]
                        recipients_tuple_list = [(4, pid) for pid in recipient_partner_ids]

                        # Construir la URL y el cuerpo (body, url, subject, etc.)
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        employee_url = f"{base_url}/web#id={employee.id}&view_type=form&model=hr.employee"
                        subject = _("🚨 ALERTA: Cuarta Falta de Asistencia - %s") % employee.name
                        body = _("""
                            El empleado **%s** (%s) ha acumulado su **CUARTA FALTA** no justificada...
                            <a href="%s" style="padding: 10px 20px; text-decoration: none; background-color: #007bff; color: white; border-radius: 5px;">Ir al Perfil del Empleado</a>
                        """) % (employee.name, employee.biometric_id or 'N/A', employee_url)
                        
                        # --- CREAR Y ENVIAR UN ÚNICO CORREO A MÚLTIPLES DESTINATARIOS ---
                        self.env['mail.mail'].sudo().create({
                            'subject': subject,
                            'body_html': body,
                            # Usar 'recipient_ids' para enviar a varios partners de una vez
                            'recipient_ids': recipients_tuple_list, 
                            # Establecer 'email_from' a la dirección del servidor para evitar rechazos
                            'email_from': self.env['ir.config_parameter'].sudo().get_param('mail.catchall.domain') or 'odooia@fruvemex.com',
                            'auto_delete': True,
                        }).send()

                        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

                        if not activity_type:
                            activity_type = self.env['mail.activity.type'].search([('name', 'in', ['To Do', 'Para hacer'])], limit=1)

                        if activity_type:
                            hr_employee_model_id = self.env['ir.model']._get('hr.employee').id
                            
                            activity_data = {
                                'res_id': employee.id,
                                'res_model_id': hr_employee_model_id,
                                'activity_type_id': activity_type.id,
                                'summary': _("🚨 Revisar: 4ta Falta de Asistencia"),
                                'note': _("El empleado **%s** ha acumulado la cuarta falta sin justificar. Debe aplicarse el protocolo de RH.") % employee.name,
                                'date_deadline': fields.Date.today(),
                            }

                            # Crear UNA actividad por CADA usuario de RRHH
                            for user_id in recipient_user_ids:
                                activity_data['user_id'] = user_id # Asigna un solo usuario por actividad
                                self.env['mail.activity'].sudo().create(activity_data)

            return
