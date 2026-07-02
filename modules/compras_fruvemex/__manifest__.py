# -*- coding: utf-8 -*-
{
    'name': "Compras Fruvemex",

    'summary': "Módulo de solicitudes de compra con flujo de aprobación",

    'description': """
Módulo para gestionar solicitudes de compra con flujo de aprobación:
- usuario_compras crea solicitudes
- encargado_compras aprueba o rechaza
- almacenista_compras marca órdenes como recibidas
    """,

    'author': "NeyiSoek",
    'website': "https://fruvemex.com/es/",
    'category': 'Purchases',
    'version': '18.0.0.1',

    'depends': [
        'base',
        'hr',
        'mail',
        'uom',
        'contacts',
        'web',
        'overtime',
        'product',
        'account',
    ],

    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/purchase_request_security_rules.xml',
        'data/purchase_request_sequence.xml',
        'views/inventory_views.xml',
        'views/purchase_request_views.xml',
        'views/purchase_rejection_wizard.xml',
        'views/purchase_receipt_wizard.xml',
        'views/compras_product_excel_import_wizard.xml',
        'views/compras_product_alert_wizard.xml',
        'views/purchase_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'compras_fruvemex/static/src/services/compras_purchase_alert_service.js',
        ],
    },

    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}


