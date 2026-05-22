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
    'depends': ['base','hr','hr_attendance', 'web','contacts','mail'],

    # always loaded
    'data': [
        'security/hr_groups.xml',
        'security/shift_management_rules.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/register_attendance_action.xml',
        'views/hr_punctuality_report_views.xml',
        'views/hr_employee.xml',
        'views/shift_management.xml',
        'views/hr_attendance.xml',
        'views/hr_leave.xml',
        'views/hr_leave_report_calendar.xml',
        'views/res_company_views.xml',
        'views/zkteco_device_views.xml',
        'views/attendance_report_wizard_views.xml',
        'views/attendance_absenteeism_wizard_views.xml',
        'views/attendance_import_wizard_views.xml',
        'views/attendance_absence_generate_wizard_views.xml',
        'views/attendance_late_weekly_report_views.xml',
        'views/zkteco_menu_views.xml',
    ],

    'assets': {
            'web.assets_backend': [
                'zkteco_realtime_connector/static/src/css/attendance_dashboard.css',
                'zkteco_realtime_connector/static/src/css/late_weekly_breakdown.css',
                'zkteco_realtime_connector/static/src/components/kanban_dashboard/attendance_kanban_dashboard.js',
                'zkteco_realtime_connector/static/src/components/kanban_dashboard/attendance_kanban_dashboard.xml',
                'zkteco_realtime_connector/static/src/fields/late_weekly_breakdown/late_weekly_breakdown_field.xml',
                'zkteco_realtime_connector/static/src/fields/late_weekly_breakdown/late_weekly_breakdown_field.js',
        

                'zkteco_realtime_connector/static/src/views/attendance_dashboard_wrapper.xml',
                'zkteco_realtime_connector/static/src/views/attendance_dashboard_wrapper.js',
        
                (
                    'after',
                    'hr_attendance/static/src/views/attendance_list_view.js',
                    'zkteco_realtime_connector/static/src/views/attendance_view_registry.js'
                ),
            ],
        },
    'demo': [],
    'installable': True,
    'application': False,
    'license':'LGPL-3',
}

