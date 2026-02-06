#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar y asignar company_id a registros existentes de overtime
"""
import sys
import os

# Añadir el directorio de Odoo al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import odoo
from odoo import api, SUPERUSER_ID

# Configuración
DB_NAME = 'odoo18Pro'
CONFIG_FILE = 'odoo.conf'

def check_and_fix_overtime_records():
    """Verifica y asigna company_id a registros de overtime que no lo tengan"""
    
    # Inicializar Odoo
    odoo.tools.config.parse_config(['-c', CONFIG_FILE, '-d', DB_NAME])
    
    with odoo.api.Environment.manage():
        registry = odoo.registry(DB_NAME)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            
            # Obtener la compañía por defecto
            default_company = env['res.company'].search([], limit=1)
            
            if not default_company:
                print("No se encontró ninguna compañía en el sistema")
                return
            
            print(f"✓ Compañía por defecto encontrada: {default_company.name} (ID: {default_company.id})")
            
            # Buscar registros de overtime sin company_id
            overtimes_without_company = env['overtime'].search([('company_id', '=', False)])
            
            print(f"\nTotal de registros de overtime: {env['overtime'].search_count([])}")
            print(f"Registros sin company_id: {len(overtimes_without_company)}")
            
            if overtimes_without_company:
                print(f"\n🔧 Asignando compañía '{default_company.name}' a {len(overtimes_without_company)} registros...\n")
                
                for overtime in overtimes_without_company:
                    overtime.company_id = default_company.id
                    print(f"   ✓ {overtime.name} - Compañía asignada")
                
                cr.commit()
                print(f"\nSe actualizaron {len(overtimes_without_company)} registros de overtime")
            else:
                print("\nTodos los registros ya tienen company_id asignado")
            
            # Verificar overtime.employee.line
            print("\n" + "="*60)
            lines_without_company = env['overtime.employee.line'].search([('company_id', '=', False)])
            
            print(f"Total de líneas de empleado: {env['overtime.employee.line'].search_count([])}")
            print(f"Líneas sin company_id: {len(lines_without_company)}")
            
            if lines_without_company:
                print(f"\n🔧 Recalculando company_id para {len(lines_without_company)} líneas...\n")
                
                # El campo company_id en las líneas es related, así que solo necesitamos forzar el recálculo
                for line in lines_without_company:
                    if line.overtime_id and line.overtime_id.company_id:
                        line._compute_company_id()
                        print(f"   ✓ Línea ID {line.id} - Compañía recalculada")
                
                cr.commit()
                print(f"\nSe actualizaron {len(lines_without_company)} líneas de empleado")
            else:
                print("\nTodas las líneas ya tienen company_id asignado")

if __name__ == '__main__':
    try:
        check_and_fix_overtime_records()
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
