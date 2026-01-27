# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from datetime import datetime, timedelta


class EmployeeBirthday(models.Model):
    _name = 'employee.birthday'
    _description = 'Calendario de Cumpleaños de Empleados'
    _auto = False
    _order = 'birthday_date DESC'

    name = fields.Char(string='Nombre', compute='_compute_name', store=False)
    employee_id = fields.Many2one('hr.employee', string='Empleado', readonly=True)
    birthday_date = fields.Date(string='Fecha de Cumpleaños', readonly=True)
    birthday_this_year = fields.Date(string='Cumpleaños Este Año', readonly=True)
    age = fields.Integer(string='Edad que Cumple', readonly=True)
    department_id = fields.Many2one('hr.department', string='Departamento', readonly=True)
    job_id = fields.Many2one('hr.job', string='Puesto', readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', readonly=True)
    biometric_id = fields.Char(string='No. Empleado', readonly=True)
    icon = fields.Char(string='Icono', compute='_compute_icon', store=False)
    
    @api.depends('employee_id', 'employee_id.name')
    def _compute_name(self):
        """Genera el nombre con formato: Cumpleaños de [Nombre Empleado]"""
        for record in self:
            if record.employee_id:
                record.name = f"🎂 Cumpleaños de {record.employee_id.name}"
            else:
                record.name = "Cumpleaños"
    
    def _compute_icon(self):
        """Asigna icono de cumpleaños"""
        for record in self:
            record.icon = '🎂'
    
    def init(self):
        """
        Crear una vista SQL que muestre los cumpleaños de los empleados
        con la fecha ajustada al año actual
        """
        tools.drop_view_if_exists(self._cr, 'employee_birthday')
        self._cr.execute("""
            CREATE OR REPLACE VIEW employee_birthday AS (
                SELECT
                    emp.id AS id,
                    emp.id AS employee_id,
                    emp.birthday AS birthday_date,
                    CASE 
                        WHEN emp.birthday IS NOT NULL THEN
                            CAST(
                                EXTRACT(YEAR FROM CURRENT_DATE) || '-' ||
                                LPAD(CAST(EXTRACT(MONTH FROM emp.birthday) AS TEXT), 2, '0') || '-' ||
                                LPAD(CAST(EXTRACT(DAY FROM emp.birthday) AS TEXT), 2, '0')
                                AS DATE
                            )
                        ELSE NULL
                    END AS birthday_this_year,
                    CASE 
                        WHEN emp.birthday IS NOT NULL THEN
                            EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM emp.birthday)
                        ELSE NULL
                    END AS age,
                    emp.department_id AS department_id,
                    emp.job_id AS job_id,
                    emp.company_id AS company_id,
                    emp.biometric_id AS biometric_id
                FROM hr_employee emp
                WHERE emp.birthday IS NOT NULL
                  AND emp.active = TRUE
            )
        """)

