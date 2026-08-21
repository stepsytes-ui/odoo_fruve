# -*- coding: utf-8 -*-

from . import models


def set_company_from_employee(env):
    records = env['enfermeria.accidente'].search([('employee_id.company_id', '!=', False)])
    for record in records:
        record.company_id = record.employee_id.company_id
