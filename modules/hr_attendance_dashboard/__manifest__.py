# -*- coding: utf-8 -*-
{
    'name': "Dashboard de Asistencia (HR Attendance Dashboard)",
    'summary': "Agrega un dashboard gráfico a la aplicación de Asistencia.",
    'description': """
        Este módulo implementa un dashboard moderno con Owl 
        para el módulo de Asistencias de Odoo.
    """,
    'author': "NeyiSoek",
    'website': "https://www.tuweb.com",
    'category': 'Human Resources/Attendances',
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',

    # Dependencias: Básico 'web' y el módulo que extendemos 'hr_attendance'
    'depends': ['hr','hr_attendance','web',],

    # Archivos de datos (XML) que siempre se cargan
    'data': [
        'views/hr_attendance_dashboard_menus.xml',
    ],

    # Assets: Aquí es donde Odoo carga tus archivos JS y XML de Owl
    'assets': {
        'web.assets_backend': [
            'hr_attendance_dashboard/static/src/main.js',
            'hr_attendance_dashboard/static/src/components/attendance_dashboard.js',
            'hr_attendance_dashboard/static/src/components/attendance_dashboard.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}