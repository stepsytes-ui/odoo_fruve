# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.tools import date_utils
from datetime import datetime, time
import pytz

# Tu constante (asegúrate de que coincida con la de tus modelos)
FIXED_DEVICE_TIMEZONE_NAME = 'America/Tijuana'

class AttendanceDashboard(http.Controller):

    def _get_local_now(self):
        """Obtiene la fecha y hora actual en la zona horaria de la compañía."""
        try:
            COMPANY_TZ = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        except pytz.UnknownTimeZoneError:
            COMPANY_TZ = pytz.utc
        return datetime.now(COMPANY_TZ)

    def _get_utc_domain_for_today(self, local_now):
        # Inicio del día (00:00:00) en la zona local
        start_of_day_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        # Fin del día (23:59:59) en la zona local
        end_of_day_local = local_now.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Convertir a UTC para la base de datos
        start_of_day_utc = start_of_day_local.astimezone(pytz.utc)
        end_of_day_utc = end_of_day_local.astimezone(pytz.utc)
        
        return [
            ('check_in', '>=', start_of_day_utc),
            ('check_in', '<=', end_of_day_utc)
        ]

    @http.route('/attendance/dashboard/get_kpis', type='json', auth='user')
    def get_kpis(self, **kw):
        """
        Ruta para obtener los 3 KPIs principales:
        Empleados, Presentes y Ausentes.
        """
        Employee = request.env['hr.employee'].sudo()
        Attendance = request.env['hr.attendance'].sudo()
        
        local_now = self._get_local_now()
        today_domain_utc = self._get_utc_domain_for_today(local_now)

        # 1. Total Empleados Activos
        total_employees = Employee.search_count([('employee_status', '=', 'active')])

        # 2. Total Presentes Hoy
        # (Cualquiera con checada de entrada 'on_time' o 'late')
        present_domain = today_domain_utc + [('punctuality_status', 'in', ['on_time', 'late'])]
        # Usamos read_group para contar empleados únicos
        present_employees = Attendance.read_group(present_domain, ['employee_id'], ['employee_id'])
        total_present = len(present_employees)

        # 3. Total Ausentes Hoy
        # (Cualquiera con checada 'absence' generada por el cron)
        absent_domain = today_domain_utc + [('punctuality_status', '=', 'absence')]
        absent_employees = Attendance.read_group(absent_domain, ['employee_id'], ['employee_id'])
        total_absent = len(absent_employees)
        
        return {
            'total_employees': total_employees,
            'total_present': total_present,
            'total_absent': total_absent,
        }

    @http.route('/attendance/dashboard/get_lists', type='json', auth='user')
    def get_lists(self, **kw):
        """
        Ruta para obtener las listas:
        - Últimos 5 registros (hoy)
        - Retardos de hoy
        """
        Attendance = request.env['hr.attendance'].sudo()
        local_now = self._get_local_now()
        today_domain_utc = self._get_utc_domain_for_today(local_now)
        
        # --- Lista 1: Últimos 5 Registros (de entrada) ---
        last_5_domain = today_domain_utc + [('punctuality_status', 'in', ['on_time', 'late'])]
        last_5_records = Attendance.search_read(
            last_5_domain,
            ['check_in_time_only', 'employee_id', 'punctuality_status'],
            limit=5,
            order='check_in desc'
        )
        # Formatear datos para que el JS los entienda fácil
        last_5_formatted = [
            {
                'time': rec['check_in_time_only'],
                'employee': rec['employee_id'][1], # [1] es el nombre
                'status': rec['punctuality_status'],
            } for rec in last_5_records
        ]

        # --- Lista 2: Retardos de Hoy ---
        lates_domain = today_domain_utc + [('punctuality_status', '=', 'late')]
        lates_records = Attendance.search_read(
            lates_domain,
            ['check_in_time_only', 'employee_id', 'punctuality_status'],
            order='check_in asc'
        )
        lates_formatted = [
            {
                'time': rec['check_in_time_only'],
                'employee': rec['employee_id'][1],
            } for rec in lates_records
        ]

        return {
            'last_5_records': last_5_formatted,
            'lates_today': lates_formatted,
        }

    @http.route('/attendance/dashboard/get_chart_data', type='json', auth='user')
    def get_chart_data(self, **kw):
        """
        Ruta para obtener los datos del gráfico de pastel.
        (Ausencias por Departamento)
        """
        Attendance = request.env['hr.attendance'].sudo()
        local_now = self._get_local_now()
        today_domain_utc = self._get_utc_domain_for_today(local_now)
        
        absent_domain = today_domain_utc + [('punctuality_status', '=', 'absence')]
        
        # Agrupar las ausencias por 'department_id' del empleado
        # Nota: 'employee_id.department_id' funciona en read_group
        absences_by_dept = Attendance.read_group(
            absent_domain,
            fields=['employee_id.department_id'], # Campo por el que agrupamos
            groupby=['employee_id.department_id'] # Campo a agrupar
        )
        
        # Formatear para Chart.js (que espera { labels: [], data: [] })
        labels = []
        data = []
        for group in absences_by_dept:
            # group['employee_id.department_id'] puede ser False si no tiene depto
            label = group['employee_id.department_id'][1] if group['employee_id.department_id'] else 'Sin Depto.'
            count = group['__count']
            
            labels.append(label)
            data.append(count)

        return {
            'labels': labels,
            'data': data,
        }