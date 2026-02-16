from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
import pytz
import logging
from io import BytesIO
import base64

_logger = logging.getLogger(__name__)

FIXED_DEVICE_TIMEZONE_NAME = 'America/Tijuana'

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    _logger.warning("openpyxl not installed. Excel generation will not work.")
    Workbook = None


class AttendanceReportWizard(models.TransientModel):
    _name = 'attendance.report.wizard'
    _description = 'Wizard para Generar Reporte de Asistencia Personalizado'

    date_from = fields.Date(string='Fecha Desde', required=True)
    date_to = fields.Date(string='Fecha Hasta', required=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado (Opcional)',
        help='Dejar en blanco para incluir todos los empleados'
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValueError(_('La fecha "Desde" no puede ser posterior a la fecha "Hasta"'))

    def action_generate_report(self):
        """Genera el reporte en Excel"""
        try:
            COMPANY_TZ = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        except pytz.UnknownTimeZoneError:
            _logger.error(f"Error: Zona horaria '{FIXED_DEVICE_TIMEZONE_NAME}' es inválida.")
            return

        date_from = self.date_from
        date_to = self.date_to
        
        # Construir dominio de empleados
        # Incluir empleados activos Y empleados inactivos que NO han sido finiquitados
        employee_domain = [
            '|',
            ('employee_status', '=', 'active'),
            '&',
            ('employee_status', '=', 'inactive'),
            ('finiquitado', '=', False),
            ('turno_id', '!=', False)
        ]
        if self.employee_id:
            employee_domain.append(('id', '=', self.employee_id.id))
        
        employees = self.env['hr.employee'].search(employee_domain)
        
        # Ordenar numéricamente por biometric_id (convertiendo a número)
        try:
            employees = sorted(employees, key=lambda e: int(e.biometric_id) if e.biometric_id else 0)
        except (ValueError, TypeError):
            # Si algún biometric_id no es válido como número, ordenar alfabéticamente
            employees = sorted(employees, key=lambda e: e.biometric_id or '')
        
        if not employees:
            raise ValueError(_('No se encontraron empleados con los criterios especificados.'))

        # Generar lista de fechas
        date_list = []
        current_date = date_from
        while current_date <= date_to:
            date_list.append(current_date)
            current_date += timedelta(days=1)

        # Crear workbook
        wb = Workbook()
        ws = wb.active
        ws.title = 'Reporte de Asistencia'

        # Estilos
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Encabezados fijos
        fixed_headers = ['No. Empleado', 'Nombre', 'Turno']
        col_num = 1
        
        for header in fixed_headers:
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_alignment
            cell.border = border
            col_num += 1

        # Encabezados dinámicos por día
        day_names = {
                0: 'Lunes',
                1: 'Martes',
                2: 'Miércoles',
                3: 'Jueves',
                4: 'Viernes',
                5: 'Sábado',
                6: 'Domingo'
            }
        
        date_columns = {}  # Mapeo de fecha a número de columna
        for date_obj in date_list:
            day_name = day_names[date_obj.weekday()]
            header_text = f'{day_name} {date_obj.day}'
            
            cell = ws.cell(row=1, column=col_num, value=header_text)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_alignment
            cell.border = border
            
            date_columns[date_obj] = col_num
            col_num += 1

        # Llenar datos
        row_num = 2
        Attendance = self.env['hr.attendance']

        for employee in employees:
            ws.cell(row=row_num, column=1, value=employee.biometric_id or '')
            ws.cell(row=row_num, column=2, value=employee.name or '')
            ws.cell(row=row_num, column=3, value=employee.sudo().turno_id.turno_name or '')

            # Aplicar bordes y alineación a celdas fijas
            for col in range(1, 4):
                cell = ws.cell(row=row_num, column=col)
                cell.border = border
                cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)

            # Llenar datos de asistencia por día
            for date_obj, col_num in date_columns.items():
                cell_data = self._get_cell_data_for_employee_date(employee, date_obj, COMPANY_TZ, Attendance)
                
                cell = ws.cell(row=row_num, column=col_num, value=cell_data['text'])
                cell.border = border
                cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
                
                # Aplicar color de fondo según el tipo
                if cell_data['color']:
                    cell.fill = PatternFill(start_color=cell_data['color'], end_color=cell_data['color'], fill_type='solid')
                
                # Aplicar color de fuente si es necesario
                if cell_data['font_color']:
                    cell.font = Font(color=cell_data['font_color'], bold=cell_data['bold'])

            row_num += 1

        # Ajustar ancho de columnas
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 20
        for col in range(4, col_num):
            ws.column_dimensions[get_column_letter(col)].width = 25

        # Guardar en BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Crear attachment
        filename = f"Reporte_Asistencia_{date_from}_{date_to}.xlsx"
        
        # Convertir a base64 para Odoo
        import base64
        file_data = base64.b64encode(output.getvalue())
        
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': file_data,
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Retornar acción para descargar
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _get_cell_data_for_employee_date(self, employee, target_date, company_tz, Attendance):
        """
        Retorna información completa para una celda: texto, color de fondo y color de fuente.
        Considera: check-ins, descanso, falta, vacaciones y todos los tipos de permiso (NEW_LEAVE_STATUS).
        Para Incapacidad, ignora los descansos del shift_management.
        """
        # PRIORIDAD MÁXIMA: Verificar si el empleado está en proceso de finiquito
        if employee.employee_status == 'inactive' and not employee.finiquitado:
            return {
                'text': 'En proceso de finiquito',
                'color': 'FF6600',  # Naranja fuerte
                'font_color': 'FFFFFF',  # Blanco
                'bold': True
            }
        
        try:
            COMPANY_TZ = company_tz
        except:
            COMPANY_TZ = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        
        # Crear rango UTC para la fecha
        start_of_day_local = COMPANY_TZ.localize(datetime.combine(target_date, time.min))
        end_of_day_local = COMPANY_TZ.localize(datetime.combine(target_date, time.max))

        start_of_day_utc = start_of_day_local.astimezone(pytz.utc)
        end_of_day_utc = end_of_day_local.astimezone(pytz.utc)

        start_utc_str = fields.Datetime.to_string(start_of_day_utc)
        end_utc_str = fields.Datetime.to_string(end_of_day_utc)

        # 1. Verificar si es día festivo global PRIMERO (tiene prioridad sobre todo)
        CalendarLeaves = self.env['resource.calendar.leaves']
        public_holiday = CalendarLeaves.search([
            ('resource_id', '=', False),  # Festivo global (aplica a todos)
            ('date_from', '<=', end_utc_str),
            ('date_to', '>=', start_utc_str)
        ], limit=1)
        
        if public_holiday:
            return {
                'text': public_holiday.name,
                'color': '4472C4',  # Azul
                'font_color': 'FFFFFF',  # Blanco
                'bold': True
            }
        
        if not employee.sudo().turno_id:
            return {'text': '', 'color': None, 'font_color': None, 'bold': False}
        
        shift = employee.sudo().turno_id
        
        # Manejo especial para turno "ESPECIAL" (gerentes/dueños)
        if shift.turno_name == 'ESPECIAL':
            # Verificar si hay checadas válidas
            valid_attendances = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_utc_str),
                ('check_in', '<=', end_utc_str),
                ('punctuality_status', 'in', ['on_time', 'late', 'LunchS', 'LunchE', 'end', 'overtime', 'n/a'])
            ], order='check_in asc')
            
            if valid_attendances:
                # Si hay checadas, mostrarlas
                check_in_times = []
                for att in valid_attendances:
                    utc_datetime = pytz.utc.localize(att.check_in)
                    local_datetime = utc_datetime.astimezone(COMPANY_TZ)
                    time_str = local_datetime.strftime("%H:%M:%S")
                    
                    if att.punctuality_status == 'n/a' and att.check_out:
                        utc_checkout = pytz.utc.localize(att.check_out)
                        local_checkout = utc_checkout.astimezone(COMPANY_TZ)
                        checkout_str = local_checkout.strftime("%H:%M:%S")
                        time_str = f"{time_str} - {checkout_str}"
                    
                    check_in_times.append(time_str)
                
                return {
                    'text': ' - '.join(check_in_times),
                    'color': '00B050',  # Verde
                    'font_color': 'FFFFFF',  # Blanco
                    'bold': False
                }
            else:
                # Si no hay checadas, mostrar palomita
                return {
                    'text': '✓',
                    'color': '00B050',  # Verde
                    'font_color': 'FFFFFF',  # Blanco
                    'bold': True
                }
        
        if shift.turno_name == 'Seguridad':

            Leave = self.env['hr.leave'].sudo()
            sickness_leave = Leave.search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
                ('holiday_status_id.name', '=', 'Incapacidad'),
                ('date_from', '<=', end_utc_str),
                ('date_to', '>=', start_utc_str)
            ], limit=1)
            
            if sickness_leave:
                return {
                    'text': 'Incapacidad',
                    'color': 'FFC000',  
                    'font_color': 'FFFFFF',  
                    'bold': True
                }
            
            approved_leave = Leave.search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', end_utc_str),
                ('date_to', '>=', start_utc_str)
            ], limit=1)
            
            if approved_leave:
                leave_name = approved_leave.holiday_status_id.name
                return {
                    'text': leave_name,
                    'color': 'FFC7CE',  # Rosa claro
                    'font_color': 'FF6600',  # Naranja oscuro
                    'bold': True
                }
            
            # 5a. Si hay check-ins válidos, mostrarlos
            valid_attendances = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_utc_str),
                ('check_in', '<=', end_utc_str),
                ('punctuality_status', 'in', ['on_time', 'late', 'LunchS', 'LunchE', 'end', 'overtime','n/a'])
            ], order='check_in asc')
            
            if valid_attendances:
                check_in_times = []
                for att in valid_attendances:
                    utc_datetime = pytz.utc.localize(att.check_in)
                    local_datetime = utc_datetime.astimezone(COMPANY_TZ)
                    time_str = local_datetime.strftime("%H:%M:%S")
                    
                    # Si es 'n/a', incluir también check_out si existe
                    if att.punctuality_status == 'n/a' and att.check_out:
                        utc_checkout = pytz.utc.localize(att.check_out)
                        local_checkout = utc_checkout.astimezone(COMPANY_TZ)
                        checkout_str = local_checkout.strftime("%H:%M:%S")
                        time_str = f"{time_str} / {checkout_str}"
                    
                    check_in_times.append(time_str)
                
                return {
                    'text': ' - '.join(check_in_times),
                    'color': '00B050',  # Verde
                    'font_color': 'FFFFFF',  # Blanco
                    'bold': False
                }
            
            # Si no hay check-ins, mostrar Descanso
            return {
                'text': 'Descanso',
                'color': None,
                'font_color': '808080',  # Gris
                'bold': False
            }
        
        day_mapping = {
            0: 'work_monday',
            1: 'work_tuesday',
            2: 'work_wednesday',
            3: 'work_thursday',
            4: 'work_friday',
            5: 'work_saturday',
            6: 'work_sunday',
        }
        day_of_week = target_date.weekday()
        field_to_check = day_mapping.get(day_of_week)
        
        # Verificar si el día es laboral (considerando también días especiales)
        is_work_day = getattr(shift, field_to_check, False)
        
        # 2. Verificar Incapacidad PRIMERO (ignora descansos del shift)
        Leave = self.env['hr.leave'].sudo()
        sickness_leave = Leave.search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('holiday_status_id.name', '=', 'Incapacidad'),
            ('date_from', '<=', end_utc_str),
            ('date_to', '>=', start_utc_str)
        ], limit=1)
        
        if sickness_leave:
            return {
                'text': 'Incapacidad',
                'color': 'FFC000',  # Amarillo/Oro
                'font_color': 'FFFFFF',  # Blanco
                'bold': True
            }
        
        # 3. Verificar otros tipos de permiso/licencia
        approved_leave = Leave.search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', end_utc_str),
            ('date_to', '>=', start_utc_str)
        ], limit=1)
        
        if approved_leave:
            # Si es domingo y NO es del departamento de seguridad, mostrar "Descanso"
            if day_of_week == 6:  # Domingo
                return {
                    'text': 'Descanso',
                    'color': None,
                    'font_color': '808080',  # Gris
                    'bold': False
                }
            # Si no es domingo, mostrar el tipo de permiso
            leave_name = approved_leave.holiday_status_id.name
            return {
                'text': leave_name,
                'color': 'FFC7CE',  # Rosa claro
                'font_color': 'FF6600',  # Naranja oscuro
                'bold': True
            }
        
        # 4. Buscar attendances
        attendances = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_utc_str),
            ('check_in', '<=', end_utc_str)
        ], order='check_in asc')
        
        # 5. Verificar si hay falta
        absence_record = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_utc_str),
            ('check_in', '<=', end_utc_str),
            ('punctuality_status', '=', 'absence')
        ], limit=1)
        
        if absence_record:
            return {
                'text': 'Falta',
                'color': 'FF0000',  # Rojo
                'font_color': 'FFFFFF',  # Blanco
                'bold': True
            }
        
        # 6. Si hay check-ins válidos, mostrarlos
        valid_attendances = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_utc_str),
            ('check_in', '<=', end_utc_str),
            ('punctuality_status', 'in', ['on_time', 'late', 'LunchS', 'LunchE', 'end', 'overtime', 'n/a'])
        ], order='check_in asc')
        
        if valid_attendances:
            check_in_times = []
            for att in valid_attendances:
                utc_datetime = pytz.utc.localize(att.check_in)
                local_datetime = utc_datetime.astimezone(COMPANY_TZ)
                time_str = local_datetime.strftime("%H:%M:%S")
                
                # Si es 'n/a', incluir también check_out si existe
                if att.punctuality_status == 'n/a' and att.check_out:
                    utc_checkout = pytz.utc.localize(att.check_out)
                    local_checkout = utc_checkout.astimezone(COMPANY_TZ)
                    checkout_str = local_checkout.strftime("%H:%M:%S")
                    time_str = f"{time_str} - {checkout_str}"
                
                check_in_times.append(time_str)
            
            return {
                'text': ' - '.join(check_in_times),
                'color': '00B050',  # Verde
                'font_color': 'FFFFFF',  # Blanco
                'bold': False
            }
        
        # 7. Si NO es un día laboral, mostrar "Descanso"
        if not is_work_day:
            return {
                'text': 'Descanso',
                'color': None,
                'font_color': '808080',  # Gris
                'bold': False
            }
        
        # 8. Si es día laboral sin check-ins y sin falta, celda vacía
        return {'text': '', 'color': None, 'font_color': None, 'bold': False}

    def _get_check_ins_for_employee_date(self, employee, target_date, company_tz, Attendance):
        """Obtiene todos los check-in times para un empleado en una fecha específica"""
        
        # Crear rango UTC para la fecha
        start_of_day_local = company_tz.localize(datetime.combine(target_date, time.min))
        end_of_day_local = company_tz.localize(datetime.combine(target_date, time.max))

        start_of_day_utc = start_of_day_local.astimezone(pytz.utc)
        end_of_day_utc = end_of_day_local.astimezone(pytz.utc)

        start_utc_str = fields.Datetime.to_string(start_of_day_utc)
        end_utc_str = fields.Datetime.to_string(end_of_day_utc)

        # Buscar attendances
        attendances = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_utc_str),
            ('check_in', '<=', end_utc_str),
            ('punctuality_status', 'in', ['on_time', 'late', 'LunchS', 'LunchE', 'end', 'overtime', 'n/a'])
        ], order='check_in asc')

        check_in_times = []
        for att in attendances:
            # Convertir a hora local
            utc_datetime = pytz.utc.localize(att.check_in)
            local_datetime = utc_datetime.astimezone(company_tz)
            time_str = local_datetime.strftime("%H:%M:%S")
            check_in_times.append(time_str)

        return check_in_times
