# -*- coding: utf-8 -*-
{
    'name': "overtime",

    'summary': "Modulo de tiempo extra",

    'description': """
Modulo con los formularios para solicitar,autorizar y calcular pagos de tiempo extra.
    """,

    'author': "NeyiSoek",
    'website': "https://fruvemex.com/es/",
    'category': 'Human Resources',
    'version': '18.0.0.1',

    'depends': ['base',
                'hr',
                'hr_attendance',
                'web',
                'contacts',
                'mail',
                'zkteco_realtime_connector',
                ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/overtime_sequence.xml',
        'views/employee_extension_daily_rate.xml',
        'views/deparment_area_upgrade.xml',
        'views/overtime_views.xml',
        'views/overtime_menu.xml',
    ],
    'assets': {
    },
    'demo': [],
    'installable': True,
    'application': False,
    'license':'LGPL-3',
}

