# -*- coding: utf-8 -*-
{
    'name': "Calendario de Cumpleaños",

    'summary': "Calendario de cumpleaños de empleados",

    'description': """
        Módulo para visualizar los cumpleaños de los empleados en un calendario.
        Muestra las fechas de cumpleaños ajustadas al año actual.
    """,

    'author': "NeyiSoek",
    'website': "https://www.fruvemex.com",

    'category': 'Human Resources',
    'version': '18.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'calendar'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/employee_birthday_views.xml',
    ],
    
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

