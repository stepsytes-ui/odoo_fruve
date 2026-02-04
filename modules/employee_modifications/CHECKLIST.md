# ✅ Checklist de Verificación Pre-Importación

## 📋 Antes de Actualizar el Módulo

- [ ] Hacer backup de la base de datos
- [ ] Verificar que xlrd esté instalado: `pip list | grep xlrd`
- [ ] Cerrar todas las sesiones activas de Odoo

## 🔄 Actualización del Módulo

- [ ] Detener el servidor Odoo
- [ ] Ejecutar: `python odoo-bin -u employee_modifications -d tu_base_datos`
- [ ] O desde interfaz: Aplicaciones → employee_modifications → Actualizar
- [ ] Verificar que no haya errores en el log
- [ ] Reiniciar el servidor si es necesario

## 📂 Preparación del Excel

- [ ] El archivo tiene extensión .xls o .xlsx
- [ ] Primera fila contiene encabezados
- [ ] Columna A: Número de Empleado (biometric_id)
- [ ] Columna B: Nombre del Empleado
- [ ] Columna C: CURP (18 caracteres)
- [ ] Columna D: RFC (12-13 caracteres)
- [ ] No hay filas vacías en medio de los datos
- [ ] No hay espacios en blanco al inicio/final de los valores

## 🔍 Validación de Datos

- [ ] Todos los números de empleado existen en Odoo
- [ ] Todos los CURP tienen exactamente 18 caracteres
- [ ] Todos los RFC tienen 12 o 13 caracteres
- [ ] No hay caracteres especiales extraños
- [ ] Los datos están en mayúsculas (o serán convertidos automáticamente)

## 🎯 Verificación en Odoo

### Verificar campos visibles:
- [ ] Ir a: Empleados → [Seleccionar empleado] → Información Privada
- [ ] Verificar que el campo "CURP" sea visible
- [ ] Verificar que el campo "RFC" sea visible

### Verificar acceso al wizard:
- [ ] Ir a: Empleados → Menú superior
- [ ] Buscar opción "Importar CURP y RFC"
- [ ] O verificar en: Empleados (menú lateral) → Importar CURP y RFC

### Verificar permisos:
- [ ] Usuario tiene rol "Recursos Humanos / Usuario"
- [ ] Usuario puede ver la pestaña "Información Privada" del empleado

## 🧪 Prueba con Datos de Ejemplo

- [ ] Usar el archivo: `ejemplo_importacion_curp_rfc.xls`
- [ ] Modificar los números de empleado con IDs reales de tu sistema
- [ ] Importar solo 2-3 registros primero
- [ ] Verificar que se actualicen correctamente
- [ ] Revisar el reporte de resultados

## 📊 Durante la Importación

- [ ] Abrir el wizard: Empleados → Importar CURP y RFC
- [ ] Seleccionar el archivo Excel
- [ ] Hacer clic en "Importar"
- [ ] Esperar a que termine el proceso
- [ ] NO cerrar la ventana hasta ver los resultados

## ✅ Después de la Importación

- [ ] Revisar estadísticas:
  - Empleados Actualizados
  - Empleados No Encontrados
  - Errores
- [ ] Revisar tabla detallada de resultados
- [ ] Verificar empleados actualizados manualmente
- [ ] Si hay errores, corregir el Excel y reimportar

## 🔧 Verificación Post-Importación

- [ ] Abrir 3-5 empleados aleatorios
- [ ] Verificar que el CURP se haya guardado correctamente
- [ ] Verificar que el RFC se haya guardado correctamente
- [ ] Ir a: Contactos → Buscar el empleado → Verificar RFC en el contacto

## 🐛 Si algo sale mal

### Error al actualizar módulo:
```bash
# Ver logs de Odoo
tail -f /var/log/odoo/odoo.log

# O revisar en la terminal donde corre Odoo
```

### Wizard no aparece:
1. Verificar que el módulo se actualizó correctamente
2. Refrescar la página (Ctrl+F5)
3. Cerrar sesión y volver a entrar
4. Verificar permisos del usuario

### Campos no visibles:
1. Ir a: Configuración → Técnico → Vistas
2. Buscar: hr.employee.form.private.info.curp.rfc.inherit
3. Verificar que esté activa

### Importación sin resultados:
1. Verificar que el archivo Excel no esté vacío
2. Revisar que los números de empleado sean correctos
3. Verificar que el campo biometric_id tenga valores

## 📝 Notas Importantes

⚠️ **IMPORTANTE**: 
- Siempre haz backup antes de importaciones masivas
- Prueba con pocos registros primero
- Verifica los resultados antes de importar todo

✅ **RECOMENDACIÓN**:
- Importar en bloques de 50-100 empleados
- Verificar cada bloque antes de continuar
- Mantener una copia del Excel original

## 📞 Soporte

Si encuentras problemas:
1. Revisar documentación: `IMPORTACION_CURP_RFC.md`
2. Ver guía rápida: `GUIA_RAPIDA.md`
3. Revisar logs de Odoo para errores detallados
4. Verificar que xlrd y xlwt estén instalados

---

✨ **¡Todo listo!** Una vez completado este checklist, puedes proceder con la importación.
