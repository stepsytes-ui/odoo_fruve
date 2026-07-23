# -*- coding: utf-8 -*-
{
    'name': "customer_polair",

    'summary': "Modulo para editar diferentes modulos de Odoo deacuerdo a las necesidades de Polair",

    'description': """
Principalmente se modifico, Compras, Ventas, Contactos, Inventario y se creo un modelo nuevo para Ordenes de trabajo.
    """,

    'author': "NeyiSoek",
    'website': "https://www.Fruvemex.com",
    'category': 'Human Resources',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts', 'hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/work_order_data.xml',
        'data/ir_cron_data.xml',
        'views/customers.xml',
        'views/work_order_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

