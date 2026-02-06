# -*- coding: utf-8 -*-

from . import controllers
from . import models

def post_init_hook(env):
    """
    Hook que se ejecuta después de instalar/actualizar el módulo
    Asigna company_id a registros existentes que no lo tengan
    """
    # Obtener la compañía por defecto
    default_company = env['res.company'].search([], limit=1)
    
    if not default_company:
        return
    
    # Actualizar registros de overtime sin company_id
    env.cr.execute("""
        UPDATE overtime 
        SET company_id = %s
        WHERE company_id IS NULL
    """, (default_company.id,))
    
    updated_count = env.cr.rowcount
    if updated_count > 0:
        print(f"✓ Se asignó company_id a {updated_count} registros de overtime existentes")
    
    # Actualizar líneas de empleado usando el company_id de su overtime padre
    env.cr.execute("""
        UPDATE overtime_employee_line oel
        SET company_id = o.company_id
        FROM overtime o
        WHERE oel.overtime_id = o.id
        AND oel.company_id IS NULL
    """)
    
    updated_lines = env.cr.rowcount
    if updated_lines > 0:
        print(f"✓ Se asignó company_id a {updated_lines} líneas de empleado existentes")
