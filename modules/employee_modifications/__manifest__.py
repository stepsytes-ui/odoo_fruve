# -*- coding: utf-8 -*-
{
    'name': "employee_modifications",

    'summary': "Fruvemex requests for employee's module",

    'description': """
Fruvemex requests for employee's module
    """,

    'author': "NeyiSoek",
    'website': "https://fruvemex.com/es/",
    'category': 'Human Resources',
    'version': '18.0.0.1',

    'depends': ['base','hr','hr_attendance', 'hr_holidays_attendance', 'web','zkteco_realtime_connector',],

    'data': [
            'security/hr_read_employees_security.xml',
            'security/ir.model.access.csv',
            'views/employee_expedient.xml', 
            'views/employee_menus.xml',
            'views/employee_disciplinary.xml',
            'views/hr_employee_views_inherit.xml',
            'views/employee_attendance_buttons_hide.xml',
            'wizard/employee_expedient_wizard_views.xml',
        ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',

}

