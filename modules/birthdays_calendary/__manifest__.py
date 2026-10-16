# -*- coding: utf-8 -*-
{
    'name': "Calendario de CumpleaÃ±os",

    'summary': "Calendario de cumpleaÃ±os de empleados",

    'description': """
        MÃ³dulo para visualizar los cumpleaÃ±os de los empleados en un calendario.
        Muestra las fechas de cumpleaÃ±os ajustadas al aÃ±o actual.
    """,

    'author': "NeyiSoek",
    'website': "https://www.fruvemex.com",

    'category': 'Human Resources',
    'version': '18.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'calendar', 'zkteco_realtime_connector'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/employee_birthday_security.xml',
        'views/employee_birthday_views.xml',
    ],
    
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

