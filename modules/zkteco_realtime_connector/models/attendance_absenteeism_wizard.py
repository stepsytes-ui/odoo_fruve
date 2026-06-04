from datetime import datetime, timedelta, time
import html as _html
import logging
import unicodedata

import pytz

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

FIXED_DEVICE_TIMEZONE_NAME = 'America/Tijuana'


class AttendanceAbsenteeismWizard(models.TransientModel):
    _name = 'attendance.absenteeism.wizard'
    _description = 'Wizard de Ausentismo'

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(
        string='Fecha Desde',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    date_to = fields.Date(
        string='Fecha Hasta',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValueError(_('La fecha "Desde" no puede ser posterior a la fecha "Hasta"'))

    def action_preview_dashboard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/attendance/absenteeism/preview/{self.id}',
            'target': 'new',
        }

    def _get_company_tz(self):
        tz_name = self.company_id.timezone or FIXED_DEVICE_TIMEZONE_NAME
        try:
            return pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            return pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)

    @staticmethod
    def _normalize_label(name):
        normalized = (name or '').strip().lower()
        normalized = unicodedata.normalize('NFKD', normalized)
        normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
        return ' '.join(normalized.split())

    @staticmethod
    def _fmt_date(date_value):
        return date_value.strftime('%d/%m/%Y') if date_value else ''

    @staticmethod
    def _fmt_date_range(date_from, date_to):
        if not date_from and not date_to:
            return ''
        if date_from == date_to:
            return AttendanceAbsenteeismWizard._fmt_date(date_from)
        return f"{AttendanceAbsenteeismWizard._fmt_date(date_from)} al {AttendanceAbsenteeismWizard._fmt_date(date_to)}"

    @staticmethod
    def _fmt_dt(dt_value, tz):
        if not dt_value:
            return ''
        if dt_value.tzinfo is None:
            dt_value = pytz.utc.localize(dt_value)
        return dt_value.astimezone(tz).strftime('%H:%M:%S')

    def _get_employee_total_for_company(self):
        Employee = self.env['hr.employee'].with_context(active_test=False)
        domain = [('company_id', '=', self.company_id.id)]

        if 'employee_status' in Employee._fields:
            domain.append(('employee_status', '=', 'active'))
        else:
            domain.append(('active', '=', True))

        return Employee.search_count(domain)

    def _get_absenteeism_data(self):
        self.ensure_one()

        company_tz = self._get_company_tz()
        date_from = self.date_from
        date_to = self.date_to

        start_local = company_tz.localize(datetime.combine(date_from, time.min))
        end_local = company_tz.localize(datetime.combine(date_to, time.max))
        start_utc = start_local.astimezone(pytz.utc)
        end_utc = end_local.astimezone(pytz.utc)
        start_utc_str = fields.Datetime.to_string(start_utc)
        end_utc_str = fields.Datetime.to_string(end_utc)

        Attendance = self.env['hr.attendance']
        Leave = self.env['hr.leave'].sudo()
        Employee = self.env['hr.employee'].with_context(active_test=False)

        active_employee_domain = [('company_id', '=', self.company_id.id)]
        if 'employee_status' in Employee._fields:
            active_employee_domain.append(('employee_status', '=', 'active'))
        else:
            active_employee_domain.append(('active', '=', True))
        active_employee_ids = set(Employee.search(active_employee_domain).ids)

        categories = {
            'vacaciones': {'label': 'Vacaciones', 'color': '#8FC5A5', 'count': 0, 'employees': set()},
            'permisos': {'label': 'Permisos', 'color': '#E7D27A', 'count': 0, 'employees': set()},
            'suspensiones': {'label': 'Suspensiones', 'color': '#E8BF7E', 'count': 0, 'employees': set()},
            'faltas': {'label': 'Faltas', 'color': '#E26A5C', 'count': 0, 'employees': set()},
            'incapacidades': {'label': 'Incapacidades', 'color': '#77ADD2', 'count': 0, 'employees': set()},
            'ingresos': {'label': 'Ingresos', 'color': "#A8FFAC", 'count': 0, 'employees': set()},
            'bajas': {'label': 'Bajas', 'color': '#EF3B88', 'count': 0, 'employees': set()},
        }

        rows_by_employee = {}
        rows_by_employee_id = {}
        punches_by_employee = {}

        def _build_or_get_row(employee, category_key, absence_type, occurrence_key=None, event_date=''):
            row_key = (employee.id, absence_type, occurrence_key or 'default')
            row = rows_by_employee.get(row_key)
            if row:
                if event_date and not row.get('event_date'):
                    row['event_date'] = event_date
                return row

            punches = punches_by_employee.get(employee.id, {})
            row = {
                'employee_id': employee.id,
                'employee_code': employee.biometric_id or '',
                'turno': employee.sudo().turno_id.turno_name or '',
                'name': employee.name or '',
                'event_date': event_date or '',
                'absence_type': absence_type,
                'absence_color': categories[category_key]['color'],
                'absence_font_color': '#FFFFFF' if category_key in ('faltas', 'incapacidades', 'bajas') else '#243447',
                'regreso': '',
                'salida': punches.get('salida', ''),
                'entrada': punches.get('entrada', ''),
            }
            rows_by_employee[row_key] = row
            rows_by_employee_id.setdefault(employee.id, []).append(row)
            return row

        def _set_category(category_key, employee, absence_type, regreso='', occurrence_key=None, event_date=''):
            categories[category_key]['employees'].add(employee.id)
            row = _build_or_get_row(
                employee,
                category_key,
                absence_type,
                occurrence_key=occurrence_key,
                event_date=event_date,
            )
            if regreso and not row['regreso']:
                row['regreso'] = regreso

        leave_category_map = {
            'vacaciones': 'vacaciones',
            'suspension': 'suspensiones',
            'incapacidad': 'incapacidades',
            'tiempo personal por enfermedad': 'incapacidades',
            'permiso pagado': 'permisos',
            'permiso de ausencia': 'permisos',
            'permiso por horas': 'permisos',
            'permiso pagado por horas': 'permisos',
            'permiso sin goce': 'permisos',
            'permiso sin goce de sueldo': 'permisos',
            'permiso con goce de sueldo': 'permisos',
            'permiso por cumpleanos': 'permisos',
            'permiso por matrimonio': 'permisos',
            'maternidad': 'permisos',
            'paternidad': 'permisos',
            'ausencia justificada (otro)': 'permisos',
        }

        approved_leaves = Leave.search([
            ('employee_id.company_id', '=', self.company_id.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', end_utc_str),
            ('date_to', '>=', start_utc_str),
        ])

        # Para evitar duplicados en permisos multi-dia, marcamos los dias cubiertos
        # por cada hr.leave aprobado (por empleado y fecha local).
        leave_dates_by_employee = {}

        for leave in approved_leaves:
            employee = leave.employee_id
            if not employee:
                continue

            leave_start_date = None
            leave_end_date = None
            if leave.date_from:
                leave_start_dt = leave.date_from
                if leave_start_dt.tzinfo is None:
                    leave_start_dt = pytz.utc.localize(leave_start_dt)
                leave_start_date = leave_start_dt.astimezone(company_tz).date()
            if leave.date_to:
                leave_end_dt = leave.date_to
                if leave_end_dt.tzinfo is None:
                    leave_end_dt = pytz.utc.localize(leave_end_dt)
                leave_end_date = leave_end_dt.astimezone(company_tz).date()

            if leave_start_date and leave_end_date:
                range_start = max(leave_start_date, date_from)
                range_end = min(leave_end_date, date_to)
                if range_start <= range_end:
                    current_day = range_start
                    while current_day <= range_end:
                        leave_dates_by_employee.setdefault(employee.id, set()).add(current_day)
                        current_day += timedelta(days=1)

            leave_name = self._normalize_label(leave.holiday_status_id.name)
            category_key = leave_category_map.get(leave_name, 'permisos')
            regreso_date = ''
            leave_event_date = ''
            if leave_start_date:
                leave_event_date = self._fmt_date(leave_start_date)
            if leave.date_to:
                leave_end = leave.date_to
                if leave_end.tzinfo is None:
                    leave_end = pytz.utc.localize(leave_end)
                regreso_date = self._fmt_date((leave_end.astimezone(company_tz).date() + timedelta(days=1)))

            _set_category(
                category_key,
                employee,
                leave.holiday_status_id.name or 'Permiso',
                regreso_date,
                occurrence_key=f'leave:{leave.id}',
                event_date=leave_event_date,
            )

        attendance_records = Attendance.search([
            ('employee_id.company_id', '=', self.company_id.id),
            ('check_in', '>=', start_utc_str),
            ('check_in', '<=', end_utc_str),
        ], order='employee_id, check_in asc')

        status_map = {
            'absence': ('faltas', 'Falta'),
            'leave_vacation': ('vacaciones', 'Vacaciones'),
            'leave_suspension': ('suspensiones', 'Suspension'),
            'leave_sickness': ('incapacidades', 'Incapacidad'),
            'leave_sickness_paid': ('incapacidades', 'Incapacidad'),
            'leave_paid': ('permisos', 'Permiso pagado'),
            'leave_abscent': ('permisos', 'Permiso de ausencia'),
            'leave_hours': ('permisos', 'Permiso por horas'),
            'leave_hours_paid': ('permisos', 'Permiso pagado por horas'),
            'leave_unpaid': ('permisos', 'Permiso sin goce'),
            'leave_birthday': ('permisos', 'Permiso por cumpleanos'),
            'leave_marriage': ('permisos', 'Permiso por matrimonio'),
            'leave_maternity': ('permisos', 'Maternidad'),
            'leave_paternity': ('permisos', 'Paternidad'),
            'leave_other': ('permisos', 'Ausencia justificada'),
        }

        for att in attendance_records:
            employee = att.employee_id
            if not employee:
                continue

            status = att.punctuality_status or ''
            if status in status_map:
                category_key, absence_label = status_map[status]
                occurrence_date = ''
                local_check_date = None
                if att.check_in:
                    check_in_dt = att.check_in
                    if check_in_dt.tzinfo is None:
                        check_in_dt = pytz.utc.localize(check_in_dt)
                    local_check_date = check_in_dt.astimezone(company_tz).date()
                    occurrence_date = local_check_date.isoformat()

                # Si el estatus de attendance es de permiso/vacaciones y ese dia ya esta
                # cubierto por un hr.leave aprobado, no creamos otro renglon.
                if status != 'absence' and local_check_date and local_check_date in leave_dates_by_employee.get(employee.id, set()):
                    continue

                _set_category(
                    category_key,
                    employee,
                    absence_label,
                    occurrence_key=f'att:{occurrence_date or att.id}',
                    event_date=self._fmt_date(local_check_date) if occurrence_date else '',
                )

            employee_punches = punches_by_employee.setdefault(employee.id, {'salida': '', 'entrada': ''})
            if status == 'LunchS' and not employee_punches['salida']:
                employee_punches['salida'] = self._fmt_dt(att.check_in, company_tz)
                for row in rows_by_employee_id.get(employee.id, []):
                    if not row['salida']:
                        row['salida'] = employee_punches['salida']
            elif status == 'LunchE' and not employee_punches['entrada']:
                employee_punches['entrada'] = self._fmt_dt(att.check_in, company_tz)
                for row in rows_by_employee_id.get(employee.id, []):
                    if not row['entrada']:
                        row['entrada'] = employee_punches['entrada']

        inactive_domain = [
            ('company_id', '=', self.company_id.id),
            ('employee_status', '=', 'inactive'),
        ]
        if 'finiquitado' in Employee._fields:
            inactive_domain.append(('finiquitado', '=', True))

        # Usar fecha de baja real para evitar que cambios administrativos (write_date)
        # cuenten al empleado como baja del dia actual.
        if 'departure_date' in Employee._fields:
            inactive_domain.extend([
                ('departure_date', '>=', date_from),
                ('departure_date', '<=', date_to),
            ])
        else:
            inactive_domain.extend([
                ('write_date', '>=', start_utc_str),
                ('write_date', '<=', end_utc_str),
            ])

        inactive_employees = Employee.search(inactive_domain)
        for employee in inactive_employees:
            departure_value = ''
            event_date = ''
            if 'departure_date' in Employee._fields and employee.departure_date:
                departure_value = fields.Date.to_string(employee.departure_date)
                event_date = self._fmt_date(employee.departure_date)
            elif employee.write_date:
                write_dt = employee.write_date
                if write_dt.tzinfo is None:
                    write_dt = pytz.utc.localize(write_dt)
                event_date = self._fmt_date(write_dt.astimezone(company_tz).date())
            _set_category(
                'bajas',
                employee,
                'Baja',
                regreso='N/A',
                occurrence_key=f'baja:{departure_value or employee.id}',
                event_date=event_date,
            )

        # Altas nuevas del dia exacto (datetime completo), evita mezclar anios anteriores.
        new_hire_domain = [
            ('company_id', '=', self.company_id.id),
            ('create_date', '>=', start_utc_str),
            ('create_date', '<=', end_utc_str),
        ]
        if 'employee_status' in Employee._fields:
            new_hire_domain.append(('employee_status', '=', 'active'))
        else:
            new_hire_domain.append(('active', '=', True))
        if 'finiquitado' in Employee._fields:
            new_hire_domain.append(('finiquitado', '=', False))

        new_hires = Employee.search(new_hire_domain)
        for employee in new_hires:
            create_value = fields.Datetime.to_string(employee.create_date) if employee.create_date else ''
            event_date = ''
            if employee.create_date:
                create_dt = employee.create_date
                if create_dt.tzinfo is None:
                    create_dt = pytz.utc.localize(create_dt)
                event_date = self._fmt_date(create_dt.astimezone(company_tz).date())
            _set_category(
                'ingresos',
                employee,
                'Ingreso',
                regreso='N/A',
                occurrence_key=f'ingreso:{create_value or employee.id}',
                event_date=event_date,
            )

        for key, info in categories.items():
            info['count'] = len(info['employees'])

        chart_total_absences = sum(info['count'] for info in categories.values())

        rows = sorted(
            [row for row in rows_by_employee.values() if row.get('absence_type')],
            key=lambda row: (
                int(row['employee_code']) if str(row['employee_code']).isdigit() else 9999999,
                row['employee_code'] or '',
                row['name'] or '',
                row['event_date'] or '',
                row['absence_type'] or '',
            ),
        )

        absence_employee_ids = set()
        for key, info in categories.items():
            if key in ('bajas', 'ingresos'):
                continue
            absence_employee_ids.update(info['employees'])

        # KPI: ausencias de empleados activos y sin duplicar por tipo de ausencia.
        total_absences = len(absence_employee_ids.intersection(active_employee_ids))
        total_employees = self._get_employee_total_for_company()
        absence_rate = (total_absences / total_employees * 100.0) if total_employees else 0.0

        def _rotation_pct(start_date, end_date):
            rotation_domain = [
                ('company_id', '=', self.company_id.id),
                ('employee_status', '=', 'inactive'),
            ]
            if 'finiquitado' in Employee._fields:
                rotation_domain.append(('finiquitado', '=', True))

            if 'departure_date' in Employee._fields:
                rotation_domain.extend([
                    ('departure_date', '>=', start_date),
                    ('departure_date', '<=', end_date),
                ])
            else:
                start_dt = company_tz.localize(datetime.combine(start_date, time.min)).astimezone(pytz.utc)
                end_dt = company_tz.localize(datetime.combine(end_date, time.max)).astimezone(pytz.utc)
                rotation_domain.extend([
                    ('write_date', '>=', fields.Datetime.to_string(start_dt)),
                    ('write_date', '<=', fields.Datetime.to_string(end_dt)),
                ])

            baja_count = Employee.search_count(rotation_domain)
            pct = (baja_count / total_employees * 100.0) if total_employees else 0.0
            return {
                'count': baja_count,
                'pct': pct,
            }

        week_start_date = date_to - timedelta(days=6)
        month_start_date = date_to.replace(day=1)
        year_start_date = date_to.replace(month=1, day=1)

        rotations = {
            'weekly': _rotation_pct(week_start_date, date_to),
            'monthly': _rotation_pct(month_start_date, date_to),
            'yearly': _rotation_pct(year_start_date, date_to),
        }

        return {
            'company_name': self.company_id.display_name,
            'date_from': date_from,
            'date_to': date_to,
            'categories': categories,
            'rows': rows,
            'total_absences': total_absences,
            'chart_total_absences': chart_total_absences,
            'total_employees': total_employees,
            'absence_rate': absence_rate,
            'rotations': rotations,
        }

    def _build_preview_html(self):
        self.ensure_one()
        data = self._get_absenteeism_data()

        categories_order = ['vacaciones', 'permisos', 'suspensiones', 'faltas', 'incapacidades', 'ingresos', 'bajas']
        pie_parts = []
        legend_html = []
        tooltips = []
        start_pct = 0.0

        total_absences = data.get('chart_total_absences', 0)
        for key in categories_order:
            item = data['categories'][key]
            pct = (item['count'] / total_absences * 100.0) if total_absences else 0.0
            end_pct = start_pct + pct
            pie_parts.append(f"{item['color']} {start_pct:.2f}% {end_pct:.2f}%")
            start_pct = end_pct

            legend_html.append(
                '<div class="legend-item">'
                f'<span class="legend-color" style="background:{item["color"]}"></span>'
                f'<span>{_html.escape(item["label"])} ({item["count"]})</span>'
                '</div>'
            )
            tooltips.append(f'{item["label"]}: {item["count"]}')

        pie_css = ', '.join(pie_parts) if pie_parts else '#e9ecef 0% 100%'
        rows_html = []
        for row in data['rows']:
            absence_style = ''
            if row.get('absence_color'):
                absence_style = (
                    f' style="background:{row["absence_color"]};'
                    f'color:{row.get("absence_font_color") or "#243447"};font-weight:700;"'
                )
            rows_html.append(
                '<tr>'
                f'<td>{_html.escape(str(row["employee_code"] or ""))}</td>'
                f'<td>{_html.escape(str(row["turno"] or ""))}</td>'
                f'<td>{_html.escape(str(row["name"] or ""))}</td>'
                f'<td>{_html.escape(str(row["event_date"] or ""))}</td>'
                f'<td{absence_style}>{_html.escape(str(row["absence_type"] or ""))}</td>'
                f'<td>{_html.escape(str(row["regreso"] or ""))}</td>'
                f'<td>{_html.escape(str(row["salida"] or ""))}</td>'
                f'<td>{_html.escape(str(row["entrada"] or ""))}</td>'
                '</tr>'
            )

        if not rows_html:
            rows_html.append('<tr><td colspan="8" class="empty">No hay ausencias para la fecha seleccionada.</td></tr>')

        html = f"""<!DOCTYPE html>
<html lang=\"es\">
<head>
<meta charset=\"UTF-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
    <title>Ausentismo {_html.escape(self._fmt_date_range(data['date_from'], data['date_to']))}</title>
<style>
:root {{
  --bg: #f3f4f6;
  --card: #ffffff;
  --text: #243447;
  --muted: #6b7280;
  --line: #d1d5db;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: 'Segoe UI', Tahoma, sans-serif; background: linear-gradient(160deg,#eef3f9 0%,#f8f9fb 100%); color: var(--text); }}
.wrapper {{ max-width: 1280px; margin: 18px auto; padding: 0 14px 24px; }}
.header {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px; box-shadow: 0 10px 22px rgba(36,52,71,.07); }}
.header h1 {{ margin: 0; font-size: 24px; }}
.header p {{ margin: 4px 0 0; color: var(--muted); font-size: 13px; }}
.kpi-grid {{ margin-top: 14px; display: grid; grid-template-columns: 1.4fr 1fr; gap: 12px; }}
.kpi-card {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 14px; box-shadow: 0 8px 18px rgba(36,52,71,.06); }}
.kpi-main {{ font-size: 28px; font-weight: 700; margin: 0; }}
.kpi-label {{ color: var(--muted); margin-top: 2px; font-size: 13px; }}
.rotation-line {{ display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dashed #e5e7eb; font-size: 14px; }}
.rotation-line:last-child {{ border-bottom: 0; }}
.chart-card {{ margin-top: 12px; background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px; box-shadow: 0 8px 18px rgba(36,52,71,.06); }}
.chart-layout {{ display: grid; grid-template-columns: 330px 1fr; gap: 14px; align-items: center; }}
.pie-wrap {{ display: flex; justify-content: center; align-items: center; }}
.pie {{ width: 290px; height: 290px; border-radius: 50%; background: conic-gradient({pie_css}); border: 4px solid #fff; box-shadow: inset 0 0 0 2px #f1f5f9, 0 10px 25px rgba(0,0,0,.08); position: relative; }}
.legend {{ display: grid; grid-template-columns: repeat(3, minmax(140px, 1fr)); gap: 9px; }}
.legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 14px; }}
.legend-color {{ width: 15px; height: 15px; border-radius: 3px; border: 1px solid rgba(0,0,0,.1); }}
.table-card {{ margin-top: 12px; background: var(--card); border: 1px solid var(--line); border-radius: 14px; box-shadow: 0 8px 18px rgba(36,52,71,.06); overflow: hidden; }}
.table-title {{ padding: 12px 14px; font-weight: 700; border-bottom: 1px solid var(--line); background: #f8fafc; }}
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; min-width: 1040px; }}
th, td {{ border-bottom: 1px solid #e5e7eb; padding: 9px 10px; font-size: 13px; text-align: left; white-space: nowrap; }}
th {{ background: #f1f5f9; color: #334155; position: sticky; top: 0; z-index: 1; }}
tr:hover td {{ background: #f8fbff; }}
.empty {{ text-align: center; color: var(--muted); padding: 18px; }}
@media (max-width: 980px) {{
  .kpi-grid {{ grid-template-columns: 1fr; }}
  .chart-layout {{ grid-template-columns: 1fr; }}
  .legend {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
}}
</style>
</head>
<body>
<div class=\"wrapper\">
  <section class=\"header\">
    <h1>Ausentismo</h1>
        <p>Empresa: {_html.escape(data['company_name'])} | Periodo: {_html.escape(self._fmt_date_range(data['date_from'], data['date_to']))}</p>
  </section>

  <section class=\"kpi-grid\">
    <div class=\"kpi-card\">
      <p class=\"kpi-main\">Total Ausencias: {data['total_absences']}/{data['total_employees']}</p>
      <p class=\"kpi-label\">Ausencia al: {data['absence_rate']:.2f}%</p>
    </div>
    <div class=\"kpi-card\">
      <div class=\"rotation-line\"><span>Rotacion Semanal:</span><strong>{data['rotations']['weekly']['count']} ({data['rotations']['weekly']['pct']:.2f}%)</strong></div>
      <div class=\"rotation-line\"><span>Rotacion Mensual:</span><strong>{data['rotations']['monthly']['count']} ({data['rotations']['monthly']['pct']:.2f}%)</strong></div>
      <div class=\"rotation-line\"><span>Rotacion Anual:</span><strong>{data['rotations']['yearly']['count']} ({data['rotations']['yearly']['pct']:.2f}%)</strong></div>
    </div>
  </section>

  <section class=\"chart-card\">
    <div class=\"chart-layout\">
      <div class=\"pie-wrap\">
                <div class=\"pie\" title=\"{' | '.join(_html.escape(x) for x in tooltips)}\"></div>
      </div>
      <div>
        <div class=\"legend\">{''.join(legend_html)}</div>
      </div>
    </div>
  </section>

  <section class=\"table-card\">
    <div class=\"table-title\">Detalle de empleados con ausentismo</div>
    <div class=\"table-wrap\">
      <table>
        <thead>
          <tr>
            <th>Empleado</th>
            <th>Turno</th>
            <th>Nombre</th>
            <th>Fecha</th>
            <th>Tipo Ausencia</th>
            <th>Regreso</th>
            <th>Salida</th>
            <th>Entrada</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>
    </div>
  </section>
</div>
</body>
</html>"""
        return html
