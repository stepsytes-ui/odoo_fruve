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
    'version': '18.0.0.4',

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
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/overtime_security_rules.xml',
        'data/overtime_sequence.xml',
        'views/employee_extension_daily_rate.xml',
        'views/deparment_area_upgrade.xml',
        'views/overtime_views.xml',
        'views/overtime_rejection_wizard.xml',
        'views/overtime_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'overtime/static/src/css/overtime_dashboard.css',
            'overtime/static/src/views/overtime_dashboard_wrapper.xml',
            'overtime/static/src/views/overtime_dashboard_wrapper.js',
            'overtime/static/src/components/overtime_dashboard/overtime_dashboard.js',
            'overtime/static/src/components/overtime_dashboard/overtime_dashboard.xml',
            # Cargar el registro DESPUÉS del JS que define la vista de lista original
            (
                'after',
                'web/static/src/views/list/list_view.js',
                'overtime/static/src/views/overtime_view_registry.js'
            ),
        ],
    },
    'demo': [],
    'installable': True,
    'application': False,
    'license':'LGPL-3',
    'post_init_hook': 'post_init_hook',
}

