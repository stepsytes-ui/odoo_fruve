-- Script SQL para verificar y corregir registros de overtime sin company_id
-- Ejecutar en PostgreSQL

-- 1. Verificar registros sin company_id
SELECT COUNT(*) as "Registros sin compañía" 
FROM overtime 
WHERE company_id IS NULL;

-- 2. Mostrar algunos registros sin company_id
SELECT id, name, requested_date, state
FROM overtime 
WHERE company_id IS NULL
LIMIT 10;

-- 3. Obtener la compañía por defecto (usualmente ID 1)
SELECT id, name 
FROM res_company 
ORDER BY id 
LIMIT 1;

-- 4. (OPCIONAL) Asignar la compañía por defecto a registros sin company_id
-- DESCOMENTA las siguientes líneas para ejecutar la actualización:
--
-- UPDATE overtime 
-- SET company_id = (SELECT id FROM res_company ORDER BY id LIMIT 1)
-- WHERE company_id IS NULL;
--
-- UPDATE overtime_employee_line 
-- SET company_id = (
--     SELECT o.company_id 
--     FROM overtime o 
--     WHERE o.id = overtime_employee_line.overtime_id
-- )
-- WHERE company_id IS NULL;
