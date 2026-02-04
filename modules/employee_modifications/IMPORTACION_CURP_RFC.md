# Importación de CURP y RFC desde Excel

## Descripción
Este módulo permite importar datos de CURP y RFC a empleados existentes en Odoo desde un archivo Excel.

## Formato del Archivo Excel

El archivo debe tener **4 columnas** en el siguiente orden:

| Columna | Nombre | Descripción | Validación |
|---------|--------|-------------|------------|
| A | Número de Empleado | Debe coincidir con el campo `biometric_id` en Odoo | Requerido |
| B | Nombre del Empleado | Nombre para referencia (no se actualiza) | Opcional |
| C | CURP | Clave Única de Registro de Población | 18 caracteres |
| D | RFC | Registro Federal de Contribuyentes con homoclave | 12 o 13 caracteres |

### Ejemplo de Archivo Excel

```
Número de Empleado | Nombre del Empleado        | CURP               | RFC
1001              | Juan Pérez García          | PEGJ850101HDFRNN05 | PEGJ850101ABC
1002              | María López Hernández      | LOHM900215MDFRNN08 | LOHM900215XY1
1003              | Carlos Rodríguez Martínez  | ROMC750512HDFRNN03 | ROMC750512AB2
```

## Campos Actualizados

### CURP
- **Campo en Odoo**: `identification_id` (hr.employee)
- **Nueva etiqueta**: "CURP"
- **Ubicación**: Empleados > Información Privada
- **Validación**: Debe tener exactamente 18 caracteres

### RFC
- **Campo en Odoo**: `rfc` (hr.employee)
- **Etiqueta**: "RFC"
- **Ubicación**: Empleados > Información Privada
- **Validación**: Debe tener 12 o 13 caracteres
- **Nota**: El RFC se almacena directamente en el empleado

## Cómo Usar el Asistente de Importación

### Opción 1: Desde el Menú Principal
1. Ir a **Empleados** > **Importar CURP y RFC**
2. Seleccionar el archivo Excel
3. Hacer clic en **Importar**
4. Revisar los resultados

### Opción 2: Desde la Vista de Lista de Empleados
1. Ir a **Empleados**
2. En la vista de lista, buscar el botón **Acción** en la parte superior
3. Seleccionar **Importar CURP y RFC**
4. Seguir los pasos anteriores

## Resultados de la Importación

Al finalizar la importación, se mostrará un resumen con:

- ✅ **Empleados Actualizados**: Cantidad de empleados que se actualizaron correctamente
- ⚠️ **Empleados No Encontrados**: Empleados del Excel que no existen en Odoo
- ❌ **Errores**: Registros con errores de validación

### Tabla Detallada
Se mostrará una tabla con cada registro procesado:
- Número de empleado
- Nombre del empleado
- Estado (Actualizado / No Encontrado / Error)
- Detalles de la acción realizada

## Validaciones

### El wizard valida:
1. **Número de empleado**: Debe existir en Odoo (campo `biometric_id`)
2. **CURP**: Debe tener exactamente 18 caracteres
3. **RFC**: Debe tener 12 o 13 caracteres
4. **Formato del archivo**: Debe ser un archivo Excel válido (.xls o .xlsx)

### Comportamiento Especial:
- Si un empleado no tiene contacto privado (`address_home_id`), se crea automáticamente
- Los valores de CURP y RFC se convierten a mayúsculas automáticamente
- La primera fila del Excel (encabezados) se omite automáticamente
- Si un campo está vacío, no se actualiza

## Requisitos

- **Librería Python**: `xlrd` (para leer archivos Excel)
- **Permisos**: Usuario con acceso al grupo "Recursos Humanos / Usuario"

## Instalación de Dependencias

Si la librería `xlrd` no está instalada, ejecutar:

```bash
pip install xlrd
```

## Notas Importantes

1. **Solo actualiza empleados existentes**: El wizard NO crea empleados nuevos
2. **Búsqueda por biometric_id**: El número de empleado debe coincidir exactamente
3. **Datos no se eliminan**: Si un campo está vacío en el Excel, el valor actual en Odoo se mantiene
4. **Respaldo recomendado**: Siempre realiza un respaldo antes de importaciones masivas
5. **Primera fila**: Asegúrate de tener encabezados en la primera fila del Excel

## Solución de Problemas

### Error: "Por favor seleccione un archivo Excel"
- Asegúrate de haber seleccionado un archivo antes de hacer clic en Importar

### Error: "Error al leer el archivo Excel"
- Verifica que el archivo sea un Excel válido (.xls o .xlsx)
- Asegúrate de que el archivo no esté corrupto

### "Empleado No Encontrado"
- Verifica que el número de empleado coincida con el campo `biometric_id` en Odoo
- Revisa que el empleado no esté archivado

### "CURP inválido" o "RFC inválido"
- CURP debe tener exactamente 18 caracteres
- RFC debe tener 12 o 13 caracteres
- Verifica que no haya espacios en blanco al inicio o final

## Ejemplos de Validación

### ✅ CURP Válido
```
PEGJ850101HDFRNN05  (18 caracteres)
LOHM900215MDFRNN08  (18 caracteres)
```

### ❌ CURP Inválido
```
PEGJ850101          (muy corto)
PEGJ850101HDFRNN051 (muy largo)
```

### ✅ RFC Válido
```
PEGJ850101ABC       (13 caracteres - persona física)
MEXC8501011A1       (12 caracteres - persona moral)
```

### ❌ RFC Inválido
```
PEGJ850101          (muy corto)
PEGJ850101ABCDE     (muy largo)
```
