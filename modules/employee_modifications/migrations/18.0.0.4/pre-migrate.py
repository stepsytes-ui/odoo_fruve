# -*- coding: utf-8 -*-


def migrate(cr, version):
    # Limpiar supervisor_id en purchase_request para evitar conflicto de foreign key
    cr.execute("""
        UPDATE purchase_request 
        SET supervisor_id = NULL
    """)
