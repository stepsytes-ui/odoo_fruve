# -*- coding: utf-8 -*-
{
    'name': "enfermeria",

    'summary': "Modulo de enfermeria",

    'description': """
Modulo de enfermeria para subir casos de accidentes y emergencias de los empleados en el sistema.
    """,

    'author': "NeyiSoek",
    'website': "https://www.Fruvemex.com",
    'category': 'Human Resources',
    'version': '18.0.0.1',


    'depends': [
        'base',
        'hr',
        'overtime',
        'zkteco_realtime_connector',
    ],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/accidentes_views.xml',
        'views/menu.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

