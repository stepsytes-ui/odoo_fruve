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
        'views/zkteco_menu_views.xml',
    ],

    'assets': {
            'web.assets_backend': [
                'zkteco_realtime_connector/static/src/css/attendance_dashboard.css',
                'zkteco_realtime_connector/static/src/components/kanban_dashboard/attendance_kanban_dashboard.js',
                'zkteco_realtime_connector/static/src/components/kanban_dashboard/attendance_kanban_dashboard.xml',
        

                'zkteco_realtime_connector/static/src/views/attendance_dashboard_wrapper.xml',
                'zkteco_realtime_connector/static/src/views/attendance_dashboard_wrapper.js',
        
                # 3. El archivo de registro, que DEBE cargarse DESPUÉS del JS de asistencia de Odoo
                (
                    'after',
                    'hr_attendance/static/src/views/attendance_list_view.js',
                    'zkteco_realtime_connector/static/src/views/attendance_view_registry.js'
                ),
            ],
        },

    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
    'application': True,
    'license':'LGPL-3',
}

