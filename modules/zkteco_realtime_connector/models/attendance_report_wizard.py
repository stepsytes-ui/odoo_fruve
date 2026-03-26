from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
import pytz
import logging
from io import BytesIO
import base64
import html as _html

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

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(string='Fecha Desde', required=True)
    date_to = fields.Date(string='Fecha Hasta', required=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado (Opcional)',
        domain="[('company_id', '=', company_id)]",
        help='Dejar en blanco para incluir todos los empleados'
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValueError(_('La fecha "Desde" no puede ser posterior a la fecha "Hasta"'))

    def action_preview_report(self):
        """Abre una vista previa HTML del reporte en una nueva pestaña del navegador"""
        return {
            'type': 'ir.actions.act_url',
            'url': f'/attendance/report/preview/{self.id}',
            'target': 'new',
        }

    def action_generate_report(self):
        """Descarga el reporte en Excel directamente sin crear archivos adjuntos"""
        return {
            'type': 'ir.actions.act_url',
            'url': f'/attendance/report/download/{self.id}',
            'target': 'self',
        }

    def _get_report_data(self):
        """
        Construye y retorna la estructura de datos del reporte.
        Usada tanto por la vista previa HTML como por la generación de Excel.
        """
        try:
            COMPANY_TZ = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        except pytz.UnknownTimeZoneError:
            raise ValueError(_(f"Zona horaria inválida: {FIXED_DEVICE_TIMEZONE_NAME}"))

        date_from = self.date_from
        date_to = self.date_to
        report_company = self.company_id or self.env.company

        if self.employee_id and self.employee_id.company_id != report_company:
            raise ValueError(
                _('El empleado seleccionado no pertenece a la empresa activa: %s')
                % report_company.display_name
            )

        employee_domain = [
            ('company_id', '=', report_company.id),
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

        try:
            employees = sorted(employees, key=lambda e: int(e.biometric_id) if e.biometric_id else 0)
        except (ValueError, TypeError):
            employees = sorted(employees, key=lambda e: e.biometric_id or '')

        if not employees:
            raise ValueError(_('No se encontraron empleados con los criterios especificados.'))

        date_list = []
        current_date = date_from
        while current_date <= date_to:
            date_list.append(current_date)
            current_date += timedelta(days=1)

        day_names = {
            0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves',
            4: 'Viernes', 5: 'Sábado', 6: 'Domingo',
        }

        Attendance = self.env['hr.attendance']
        rows = []
        for employee in employees:
            cells = {}
            for date_obj in date_list:
                cells[date_obj] = self._get_cell_data_for_employee_date(
                    employee, date_obj, COMPANY_TZ, Attendance
                )
            rows.append({
                'biometric_id': employee.biometric_id or '',
                'name': employee.name or '',
                'turno': employee.sudo().turno_id.turno_name or '',
                'cells': cells,
            })

        return {
            'date_list': date_list,
            'day_names': day_names,
            'rows': rows,
            'date_from': date_from,
            'date_to': date_to,
            'company': report_company,
            'company_tz': COMPANY_TZ,
        }

    def _build_preview_html(self):
        """Genera el HTML completo de la vista previa del reporte"""
        data = self._get_report_data()
        date_list = data['date_list']
        day_names = data['day_names']
        rows = data['rows']
        date_from = data['date_from']
        date_to = data['date_to']

        def cell_style(color, font_color, bold):
            styles = [
                'padding:4px 6px',
                'border:1px solid #ccc',
                'white-space:pre-line',
                'font-size:11px',
                'vertical-align:top',
                'line-height:1.4',
            ]
            if color:
                styles.append(f'background-color:#{color}')
            if font_color:
                styles.append(f'color:#{font_color}')
            if bold:
                styles.append('font-weight:bold')
            return '; '.join(styles)

        def esc(val):
            return _html.escape(str(val or ''))

        parts = []
        parts.append(f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vista Previa Asistencia {esc(str(date_from))} – {esc(str(date_to))}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; font-size: 13px; background: #f0f2f5; }}
  .toolbar {{
    position: sticky; top: 0; z-index: 200;
    background: #fff; padding: 8px 16px;
    border-bottom: 2px solid #4472C4;
    display: flex; align-items: center; gap: 12px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.12);
  }}
  .toolbar h2 {{ flex: 1; font-size: 14px; color: #1a2b4a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .toolbar .meta {{ font-size: 11px; color: #6c757d; white-space: nowrap; }}
  .btn {{ padding: 6px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; text-decoration: none; display: inline-block; font-weight: 600; }}
  .btn-primary {{ background: #4472C4; color: #fff; }}
  .btn-primary:hover {{ background: #2e57a8; }}
  .legend {{
    background: #fff; padding: 6px 16px; position: sticky; top: 44px; z-index: 190;
    border-bottom: 1px solid #dde;
    display: flex; flex-wrap: wrap; gap: 14px; align-items: center;
    font-size: 11px; color: #444;
  }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; }}
  .lswatch {{ width: 13px; height: 13px; border-radius: 2px; border: 1px solid rgba(0,0,0,0.2); display: inline-block; flex-shrink: 0; }}
  .table-wrap {{ overflow: auto; max-height: calc(100vh - 92px); }}
  table {{ border-collapse: collapse; background: #fff; min-width: 100%; }}
  th, td {{ border: 1px solid #ccc; font-size: 11px; }}
  th {{
    background: #4472C4; color: #fff;
    padding: 5px 7px; white-space: nowrap;
    position: sticky; top: 0; z-index: 10;
    text-align: center;
  }}
  td {{ padding: 4px 6px; vertical-align: top; }}
  .s0 {{ position: sticky; left: 0;   z-index: 5; background: inherit; min-width: 75px;  max-width: 75px; }}
  .s1 {{ position: sticky; left: 75px; z-index: 5; background: inherit; min-width: 170px; max-width: 170px; }}
  .s2 {{ position: sticky; left: 245px; z-index: 5; background: inherit; min-width: 110px; max-width: 110px; }}
  th.s0, th.s1, th.s2 {{ z-index: 20; }}
  .day-cell {{ min-width: 95px; max-width: 130px; }}
  tr:nth-child(even) td {{ background-color: #f9f9fb; }}
  tr:hover td {{ background-color: #eef3ff !important; }}
</style>
</head>
<body>
<div class="toolbar">
  <h2>&#128203; Vista Previa &mdash; Reporte de Asistencia</h2>
  <span class="meta">{esc(str(date_from))} al {esc(str(date_to))} &bull; {len(rows)} empleado(s)</span>
  <a class="btn btn-primary" href="/attendance/report/download/{self.id}">&#11015; Descargar Excel</a>
</div>
<div class="legend">
  <strong>Leyenda:</strong>
  <div class="legend-item"><span class="lswatch" style="background:#00B050"></span>Asistencia</div>
  <div class="legend-item"><span class="lswatch" style="background:#FF0000"></span>Falta</div>
  <div class="legend-item"><span class="lswatch" style="background:#FFC000"></span>Incapacidad</div>
  <div class="legend-item"><span class="lswatch" style="background:#FFC7CE"></span><span style="color:#FF6600">Permiso</span></div>
  <div class="legend-item"><span class="lswatch" style="background:#4472C4"></span>Festivo</div>
  <div class="legend-item"><span class="lswatch" style="background:#FF6600"></span>En finiquito</div>
  <div class="legend-item"><span class="lswatch" style="background:#fff"></span><span style="color:#808080">Descanso</span></div>
</div>
<div class="table-wrap">
<table>
<thead><tr>
  <th class="s0">No. Emp.</th>
  <th class="s1">Nombre</th>
  <th class="s2">Turno</th>
''')

        for date_obj in date_list:
            day_name = day_names[date_obj.weekday()]
            parts.append(
                f'  <th class="day-cell">{esc(day_name)}<br>'
                f'<span style="font-weight:normal;font-size:10px">{date_obj.strftime("%d/%m")}</span></th>\n'
            )

        parts.append('</tr></thead>\n<tbody>\n')

        for row in rows:
            parts.append('<tr>\n')
            parts.append(f'  <td class="s0">{esc(row["biometric_id"])}</td>\n')
            parts.append(f'  <td class="s1">{esc(row["name"])}</td>\n')
            parts.append(f'  <td class="s2">{esc(row["turno"])}</td>\n')
            for date_obj in date_list:
                cell = row['cells'].get(date_obj, {})
                style = cell_style(cell.get('color'), cell.get('font_color'), cell.get('bold', False))
                text = esc(cell.get('text', '') or '')
                parts.append(f'  <td class="day-cell" style="{style}">{text}</td>\n')
            parts.append('</tr>\n')

        parts.append('</tbody>\n</table>\n</div>\n</body>\n</html>')
        return ''.join(parts)

    def _generate_excel_file(self):
        """Genera el archivo Excel y retorna (bytes_data, filename) sin crear adjuntos."""
        if Workbook is None:
            raise ImportError('openpyxl no está instalado. Instálelo con: pip install openpyxl')

        data = self._get_report_data()
        date_list = data['date_list']
        day_names = data['day_names']
        rows = data['rows']
        date_from = data['date_from']
        date_to = data['date_to']

        wb = Workbook()
        ws = wb.active
        ws.title = 'Reporte de Asistencia'

        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        fixed_headers = ['No. Empleado', 'Nombre', 'Turno']
        col_num = 1
        for header in fixed_headers:
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_alignment
            cell.border = border
            col_num += 1

        date_columns = {}
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

        total_cols = col_num

        row_num = 2
        for row in rows:
            ws.cell(row=row_num, column=1, value=row['biometric_id'])
            ws.cell(row=row_num, column=2, value=row['name'])
            ws.cell(row=row_num, column=3, value=row['turno'])

            for col in range(1, 4):
                cell = ws.cell(row=row_num, column=col)
                cell.border = border
                cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)

            for date_obj, col_idx in date_columns.items():
                cell_data = row['cells'].get(date_obj, {})
                cell = ws.cell(row=row_num, column=col_idx, value=cell_data.get('text', '') or '')
                cell.border = border
                cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
                if cell_data.get('color'):
                    cell.fill = PatternFill(
                        start_color=cell_data['color'],
                        end_color=cell_data['color'],
                        fill_type='solid'
                    )
                if cell_data.get('font_color'):
                    cell.font = Font(color=cell_data['font_color'], bold=cell_data.get('bold', False))

            row_num += 1

        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 20
        for col in range(4, total_cols):
            ws.column_dimensions[get_column_letter(col)].width = 25

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f'Reporte_Asistencia_{date_from}_{date_to}.xlsx'
        return output.getvalue(), filename

    def _get_cell_data_for_employee_date(self, employee, target_date, company_tz, Attendance):
        """
        Retorna información completa para una celda: texto, color de fondo y color de fuente.
        Considera: check-ins, descanso, falta, vacaciones y todos los tipos de permiso (NEW_LEAVE_STATUS).
        Para Incapacidad, ignora los descansos del shift_management.
        """
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

        descanso_statuses = ['leave_day_off', 'Descanso', 'descanso']
        incapacidad_statuses = ['leave_sickness', 'leave_sickness_paid', 'Incapacidad', 'incapacidad']

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
            # Respetar Incapacidad/Descanso registrados en attendance.
            sickness_attendance = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_utc_str),
                ('check_in', '<=', end_utc_str),
                ('punctuality_status', 'in', incapacidad_statuses)
            ], limit=1)

            if sickness_attendance:
                return {
                    'text': 'Incapacidad',
                    'color': 'FFC000',
                    'font_color': 'FFFFFF',
                    'bold': True
                }

            descanso_attendance = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_utc_str),
                ('check_in', '<=', end_utc_str),
                ('punctuality_status', 'in', descanso_statuses)
            ], limit=1)

            if descanso_attendance:
                return {
                    'text': 'Descanso',
                    'color': None,
                    'font_color': '808080',
                    'bold': False
                }

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

            sickness_attendance = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_utc_str),
                ('check_in', '<=', end_utc_str),
                ('punctuality_status', 'in', incapacidad_statuses)
            ], limit=1)
            
            if sickness_leave or sickness_attendance:
                return {
                    'text': 'Incapacidad',
                    'color': 'FFC000',  
                    'font_color': 'FFFFFF',  
                    'bold': True
                }

            descanso_attendance = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_utc_str),
                ('check_in', '<=', end_utc_str),
                ('punctuality_status', 'in', descanso_statuses)
            ], limit=1)

            if descanso_attendance:
                return {
                    'text': 'Descanso',
                    'color': None,
                    'font_color': '808080',
                    'bold': False
                }
            
            approved_leave = Leave.search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', end_utc_str),
                ('date_to', '>=', start_utc_str)
            ], limit=1)
            
            if approved_leave:
                leave_name = approved_leave.holiday_status_id.name
                if leave_name.strip().lower() == 'descanso':
                    return {
                        'text': 'Descanso',
                        'color': None,
                        'font_color': '808080',  # Gris
                        'bold': False
                    }
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

        sickness_attendance = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_utc_str),
            ('check_in', '<=', end_utc_str),
            ('punctuality_status', 'in', incapacidad_statuses)
        ], limit=1)
        
        if sickness_leave or sickness_attendance:
            return {
                'text': 'Incapacidad',
                'color': 'FFC000',  # Amarillo/Oro
                'font_color': 'FFFFFF',  # Blanco
                'bold': True
            }

        # 3. Verificar Descanso en hr.attendance (si existe, marcar descanso)
        descanso_attendance = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_utc_str),
            ('check_in', '<=', end_utc_str),
            ('punctuality_status', 'in', descanso_statuses)
        ], limit=1)

        if descanso_attendance:
            return {
                'text': 'Descanso',
                'color': None,
                'font_color': '808080',  # Gris
                'bold': False
            }
        
        # 4. Verificar otros tipos de permiso/licencia
        approved_leave = Leave.search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', end_utc_str),
            ('date_to', '>=', start_utc_str)
        ], limit=1)
        
        if approved_leave:
            leave_name = approved_leave.holiday_status_id.name
            # Descanso desde hr.leave → cuadro blanco, texto gris
            if leave_name.strip().lower() == 'descanso' or day_of_week == 6:
                return {
                    'text': 'Descanso',
                    'color': None,
                    'font_color': '808080',  # Gris
                    'bold': False
                }
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
        
        # 8. Si es día laboral sin check-ins y sin falta
        # Aquí sí verificamos si está en proceso de finiquito (solo para días laborales sin asistencia)
        if employee.employee_status == 'inactive' and not employee.finiquitado:
            return {
                'text': 'En proceso de finiquito',
                'color': 'FF6600',  # Naranja fuerte
                'font_color': 'FFFFFF',  # Blanco
                'bold': True
            }
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
