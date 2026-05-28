# -*- coding: utf-8 -*-

import base64
import logging
from io import BytesIO

from odoo import _, fields, models
from odoo.exceptions import UserError

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
except ImportError:
    Workbook = None


_logger = logging.getLogger(__name__)


class ExportEmployeeListWizard(models.TransientModel):
    _name = 'export.employee.list.wizard'
    _description = 'Asistente para exportar lista de empleados'

    employee_status_filter = fields.Selection(
        [
            ('active', 'Activos'),
            ('inactive', 'Inactivos'),
        ],
        string='Mostrar empleados',
        required=True,
        default='active',
    )

    archivo_excel = fields.Binary(
        string='Archivo Excel',
        readonly=True,
        attachment=False,
    )

    nombre_archivo = fields.Char(
        string='Nombre del Archivo',
        readonly=True,
    )

    def _get_employees(self):
        self.ensure_one()
        domain = [('active', '=', self.employee_status_filter == 'active')]
        employees = self.env['hr.employee'].with_context(active_test=False).search(domain)

        def sort_key(employee):
            biometric_value = (employee.biometric_id or '').strip()
            if biometric_value.isdigit():
                number_key = (0, int(biometric_value))
            else:
                number_key = (1, biometric_value)
            return number_key + ((employee.name or '').strip(), employee.id)

        return employees.sorted(key=sort_key)

    def _generate_excel_file(self):
        if Workbook is None:
            raise UserError(_('openpyxl no está instalado. Instale la dependencia para exportar Excel.'))

        employees = self._get_employees()

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Lista de Empleados'

        header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        left_alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin'),
        )

        headers = ['No. Empleado', 'Nombre', 'CURP', 'RFC', 'IMSS', 'Estado']
        for column_index, header in enumerate(headers, start=1):
            cell = sheet.cell(row=1, column=column_index, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_alignment
            cell.border = border

        for row_index, employee in enumerate(employees, start=2):
            row_values = [
                employee.biometric_id or '',
                employee.name or '',
                employee.identification_id or '',
                employee.rfc or '',
                employee.ssnid or '',
                'Activo' if employee.active else 'Inactivo',
            ]
            for column_index, value in enumerate(row_values, start=1):
                cell = sheet.cell(row=row_index, column=column_index, value=value)
                cell.alignment = left_alignment
                cell.border = border

        sheet.freeze_panes = 'A2'
        sheet.auto_filter.ref = sheet.dimensions
        sheet.column_dimensions['A'].width = 16
        sheet.column_dimensions['B'].width = 32
        sheet.column_dimensions['C'].width = 24
        sheet.column_dimensions['D'].width = 22
        sheet.column_dimensions['E'].width = 18
        sheet.column_dimensions['F'].width = 14

        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        status_suffix = 'activos' if self.employee_status_filter == 'active' else 'inactivos'
        return output.getvalue(), f'lista_datos_empleados_{status_suffix}.xlsx'

    def action_export_excel(self):
        self.ensure_one()

        excel_bytes, filename = self._generate_excel_file()
        self.write({
            'archivo_excel': base64.b64encode(excel_bytes),
            'nombre_archivo': filename,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=export.employee.list.wizard&id={self.id}&field=archivo_excel&filename_field=nombre_archivo&download=true',
            'target': 'self',
        }