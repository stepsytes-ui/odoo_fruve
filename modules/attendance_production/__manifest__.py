# -*- coding: utf-8 -*-
{
    'name': "Asistencia solo producción",

    'summary': "Módulo para restringir la vista de asistencia del personal de Producción a un grupo específico de administrativos.",
    'author': "NeyiSoek",
    'website': "https://www.fruvemex.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_attendance'],

    # always loaded
    'data': [
        'security/groups.xml',
        # 'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'views/production_attendance_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

