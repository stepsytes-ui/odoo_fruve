# -*- coding: utf-8 -*-
{
    'name': "zkteco_realtime_connector",

    'summary': "Aplicacion de prueba para obtener datos del checador",

    'description': """
Modulo para integración de ZKTeco en odoo
    """,

    'author': "NeyiSoek",
    'website': "https://www.Fruvemex.com",
    'category': 'Human Resources',
    'version': '18.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_attendance', 'web',],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/hr_punctuality_report_views.xml',
        'views/hr_employee.xml',
        'views/shift_management.xml',
        'views/hr_attendance.xml',
        'views/res_company_views.xml',
        'views/zkteco_device_views.xml',
        # 'views/attendance_dashboard_views.xml',
        'views/zkteco_menu_views.xml',
    ],

    # 'assets': {
    #     'web.assets_backend': [
    #         # SCSS
    #         'zkteco_realtime_connector/static/src/scss/dashboard.scss',
            
    #         # JS (¡El más importante para tu error!)
    #         'zkteco_realtime_connector/static/src/js/dashboard_service.js',
    #         'zkteco_realtime_connector/static/src/js/attendance_dashboard.js', # <-- ESTE ARCHIVO ES EL QUE FALLA

    #         # XML (Plantilla QWeb)
    #         'zkteco_realtime_connector/static/src/xml/attendance_dashboard.xml',
    #     ],
    # },

    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
    'application': True,
    'license':'LGPL-3',
}

