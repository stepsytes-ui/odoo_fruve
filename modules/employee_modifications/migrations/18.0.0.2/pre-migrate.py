# -*- coding: utf-8 -*-

def migrate(cr, version):
    """
    Migración para convertir supervisor_id de hr.employee a res.users en hr_leave,
    hr_suspension, hr_incapacity, hr_permission y hr_vacation
    """
    # Lista de tablas que necesitan migración
    tables_to_migrate = ['hr_leave', 'hr_suspension', 'hr_incapacity', 'hr_permission', 'hr_vacation']
    
    for table_name in tables_to_migrate:
        # Verificar si la tabla existe
        cr.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name=%s
        """, (table_name,))
        
        if not cr.fetchone():
            print(f"Tabla {table_name} no existe, saltando...")
            continue
        
        # Verificar si la columna supervisor_id existe en la tabla
        cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name=%s AND column_name='supervisor_id'
        """, (table_name,))
        
        if not cr.fetchone():
            print(f"Columna supervisor_id no existe en {table_name}, saltando...")
            continue
        
        # 1. Primero, eliminar la foreign key constraint antigua si existe
        cr.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = %s
            AND constraint_type = 'FOREIGN KEY'
            AND constraint_name LIKE '%%supervisor_id%%'
        """, (table_name,))
        
        constraint = cr.fetchone()
        if constraint:
            constraint_name = constraint[0]
            cr.execute(f'ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS "{constraint_name}"')
            print(f"Constraint {constraint_name} eliminada de {table_name}")
        
        # 2. Actualizar supervisor_id de hr.employee.id a res.users.id
        # usando el campo user_id del empleado
        cr.execute(f"""
            UPDATE {table_name}
            SET supervisor_id = he.user_id
            FROM hr_employee he
            WHERE {table_name}.supervisor_id = he.id
            AND he.user_id IS NOT NULL
        """)
        
        rows_updated = cr.rowcount
        print(f"  {rows_updated} registros actualizados en {table_name}")
        
        # 3. Establecer NULL para registros donde el empleado no tiene usuario asociado
        # o donde el supervisor_id no corresponde a un empleado válido
        cr.execute(f"""
            UPDATE {table_name}
            SET supervisor_id = NULL
            WHERE supervisor_id IS NOT NULL
            AND supervisor_id NOT IN (SELECT id FROM res_users)
        """)
        
        rows_nullified = cr.rowcount
        if rows_nullified > 0:
            print(f"  {rows_nullified} registros con supervisor inválido establecidos a NULL en {table_name}")
    
    print(f"Migración completada: supervisor_id convertido de hr.employee a res.users")
