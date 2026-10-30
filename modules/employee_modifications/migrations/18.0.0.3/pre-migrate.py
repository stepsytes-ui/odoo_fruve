# -*- coding: utf-8 -*-


def migrate(cr, version):
    cr.execute("""
        ALTER TABLE employee_warning
        DROP CONSTRAINT IF EXISTS employee_warning_supervisor_id_fkey
    """)
    cr.execute("""
        ALTER TABLE employee_warning
        ALTER COLUMN supervisor_id DROP NOT NULL
    """)
    # Convierte res.users a employee.supervisor; si no hay coincidencia queda vacio
    cr.execute("""
        UPDATE employee_warning warning
        SET supervisor_id = (
            SELECT supervisor.id
            FROM hr_employee employee
            JOIN employee_supervisor supervisor
                ON supervisor.employee_id = employee.id
                AND supervisor.company_id = employee.company_id
            WHERE employee.user_id = warning.supervisor_id
                AND employee.company_id = warning.company_id
            ORDER BY supervisor.id
            LIMIT 1
        )
        WHERE warning.supervisor_id IS NOT NULL
    """)
