# -*- coding: utf-8 -*-
{
    'name': "security_view",

    'summary': "Modulo de la vista de permisos autorizados de empleados para poder ser visualizados por seguridad",

    'author': "NeyiSoek",
    'website': "https://www.fruvemex.com",
    'category': 'Human Resources',
    'version': '0.1',
    'depends': ['base', 'hr','hr_attendance','hr_holidays','zkteco_realtime_connector'],

    'data': [
        'security/security.xml',
        'security/hr_leave_guardia_rules.xml',
        'security/employee_field_restrictions.xml',
        'security/hr_leave_guardia_field_restrictions.xml',
        'security/ir.model.access.csv',
        'views/time_off_security_view.xml',
        'views/time_off_security_menu.xml',
        'views/hr_leave_name_fix.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

