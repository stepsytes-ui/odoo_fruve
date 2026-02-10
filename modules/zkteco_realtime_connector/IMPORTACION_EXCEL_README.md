# Wizard de Importación de Excel de Checadas

## Descripción General

Este wizard permite importar un archivo Excel con checadas de empleados y generar automáticamente un reporte de asistencias con análisis inteligente de horarios.

## Características Principales

### 1. Importación de Excel
- Soporta archivos Excel (.xlsx)
- Lee checadas de múltiples empleados
- Automáticamente agrupa checadas por empleado y fecha
- Detecta y procesa diferentes formatos de fecha/hora

### 2. Formato del Archivo Excel

El archivo Excel debe contener las siguientes columnas (en orden):

| Columna | Contenido | Ejemplo |
|---------|-----------|---------|
| A | Número de Empleado | 1001 |
| B | Nombre del Empleado | Juan Pérez |
| C | Departamento | Producción |
| D | Fecha y Hora de Checada | 2026-02-10 08:00:00 |

**Formatos de fecha soportados:**
- `YYYY-MM-DD HH:MM:SS` (2026-02-10 08:00:00)
- `DD/MM/YYYY HH:MM:SS` (10/02/2026 08:00:00)
- `MM/DD/YYYY HH:MM:SS` (02/10/2026 08:00:00)
- `YYYY-MM-DD HH:MM` (2026-02-10 08:00)

### 3. Lógica de Análisis Automático

El sistema analiza las checadas y aplica colores automáticamente según estas reglas:

#### 🟢 **Verde - Jornada Completa**
- **Condición**: Más de 8 horas entre la primera y última checada del día
- **Muestra**: Primera checada - Última checada
- **Ejemplo**: `08:00:00 - 17:30:00`
- **Interpretación**: El empleado cumplió su jornada laboral completa

#### 🟡 **Amarillo - Jornada Incompleta**
- **Condición**: Solo una checada O menos de 8 horas entre checadas
- **Muestra**: 
  - Una sola hora si solo hay una checada: `08:00:00`
  - Primera y última si hay varias pero < 8 horas: `08:00:00 - 14:00:00`
- **Interpretación**: Posible jornada incompleta, requiere revisión

#### ⚪ **Gris - Descanso**
- **Condición**: Día domingo sin checadas
- **Excepción**: Si el turno es "Seguridad", también se considera descanso
- **Muestra**: `Descanso`
- **Interpretación**: Día de descanso programado

#### 🔵 **Azul Claro - Pendiente de Comprobar**
- **Condición**: El empleado no tiene checadas en un día donde otros empleados SÍ tienen
- **Muestra**: `Pendiente de comprobar`
- **Interpretación**: Posible falta o permiso no registrado, requiere validación de RH
- **Ejemplo**: Si 20 empleados checaron el sábado pero uno no, probablemente ese empleado faltó

#### **Sin Color - Sin Información**
- **Condición**: Ningún empleado tiene checadas ese día
- **Muestra**: (celda vacía)
- **Interpretación**: Probablemente día no laboral

## Cómo Usar el Wizard

### Paso 1: Acceder al Wizard
1. Ir a **ZKTeco** → **Importar Excel de Checadas**
2. Se abrirá una ventana emergente

### Paso 2: Cargar el Archivo
1. Hacer clic en el campo "Archivo Excel"
2. Seleccionar el archivo Excel con las checadas
3. El archivo debe tener el formato especificado arriba

### Paso 3: Definir Rango de Fechas
1. **Fecha Desde**: Primera fecha a incluir en el reporte
2. **Fecha Hasta**: Última fecha a incluir en el reporte
3. El reporte mostrará todos los días entre estas fechas

### Paso 4: Generar Reporte
1. Hacer clic en **"Generar Reporte"**
2. El sistema procesará el Excel y generará el reporte
3. Automáticamente se descargará un archivo Excel con el reporte

## Estructura del Reporte Generado

### Columnas Fijas
- **No. Empleado**: Número de identificación del empleado
- **Nombre**: Nombre completo del empleado
- **Departamento**: Departamento al que pertenece
- **Turno**: Turno asignado (obtenido de Odoo si el empleado existe)

### Columnas Dinámicas
- Una columna por cada día en el rango de fechas
- Encabezado: `Día Número` (ej: "Lunes 10", "Martes 11")
- Contenido: Checadas y/o estado según la lógica de colores

## Ejemplos de Uso

### Ejemplo 1: Empleado con Jornada Completa
**Excel de entrada:**
```
1001 | Juan Pérez | Producción | 2026-02-10 08:00:00
1001 | Juan Pérez | Producción | 2026-02-10 17:30:00
```

**Reporte generado:**
- Celda en **verde** con texto: `08:00:00 - 17:30:00`
- Diferencia: 9.5 horas ✓

### Ejemplo 2: Empleado con Solo una Checada
**Excel de entrada:**
```
1002 | María García | Almacén | 2026-02-10 08:00:00
```

**Reporte generado:**
- Celda en **amarillo** con texto: `08:00:00`
- Solo una checada, requiere revisión

### Ejemplo 3: Detección de Posibles Faltas
**Situación:**
- 15 empleados tienen checadas el sábado 8 de febrero
- 1 empleado NO tiene checadas ese día

**Reporte generado para ese empleado:**
- Celda en **azul claro** con texto: `Pendiente de comprobar`
- RH debe validar si fue falta, permiso o ausencia justificada

### Ejemplo 4: Domingo (Descanso)
**Situación:**
- Es domingo 9 de febrero
- El empleado no tiene checadas

**Reporte generado:**
- Celda en **gris** con texto: `Descanso`
- Día de descanso normal

### Ejemplo 5: Guardias de Seguridad
**Situación:**
- Turno: "Seguridad"
- Domingo con checadas

**Reporte generado:**
- Se muestran las checadas normalmente con colores verde/amarillo
- No se marca como descanso automáticamente

## Validaciones y Consideraciones

### Validaciones Automáticas
1. **Fechas**: La fecha "Desde" no puede ser posterior a la fecha "Hasta"
2. **Archivo requerido**: Debe cargar un archivo Excel
3. **Formato de Excel**: Debe ser un archivo .xlsx válido
4. **Datos mínimos**: Debe haber al menos un empleado en el Excel

### Manejo de Errores
- Si una fila tiene formato de fecha inválido, se omite con warning en log
- Si un empleado no existe en Odoo, el turno aparece como "N/A"
- Si hay errores al leer el Excel, se muestra mensaje de error claro

### Integración con Odoo
- **Empleados**: Se busca el empleado en Odoo por `biometric_id` (número de empleado)
- **Turnos**: Se obtiene el turno asignado al empleado en Odoo
- Si el empleado no existe en Odoo, aún se procesa pero el turno será "N/A"

## Diferencias con el Reporte Normal de Asistencias

| Característica | Reporte Normal | Reporte de Importación |
|----------------|----------------|------------------------|
| Fuente de datos | Base de datos Odoo | Archivo Excel externo |
| Filtro de empleados | Por empleado específico o todos | Por empleados en Excel |
| Análisis de horas | Muestra todas las checadas | Analiza primera y última |
| Detección de faltas | Basado en configuración de turnos | Basado en patrones de otros empleados |
| Uso típico | Reporte diario/semanal operativo | Validación de datos externos/importación masiva |

## Casos de Uso Recomendados

1. **Importación desde sistemas externos**: Si tienes checadas de un sistema externo (no ZKTeco)
2. **Validación de datos**: Verificar checadas antes de importarlas al sistema principal
3. **Análisis de patrones**: Detectar empleados con jornadas incompletas o ausencias no justificadas
4. **Auditorías**: Generar reportes de períodos pasados desde archivos históricos
5. **Migración de datos**: Importar checadas históricas de otro sistema

## Solución de Problemas

### El reporte no se genera
**Posibles causas:**
- Archivo Excel corrupto o en formato incorrecto
- No hay datos en el rango de fechas especificado
- Error en formato de fechas en el Excel

**Solución:**
- Verificar que el Excel tiene las 4 columnas requeridas
- Verificar formato de fechas en columna D
- Revisar logs del servidor para detalles del error

### Todos los días aparecen en azul "Pendiente de comprobar"
**Causa:** No hay checadas de ningún empleado en esos días

**Solución:** Esto es normal si el Excel no incluye checadas para esas fechas

### Empleados sin turno (N/A)
**Causa:** El empleado no existe en Odoo o no tiene `biometric_id` configurado

**Solución:** 
- Crear el empleado en Odoo
- Asignar el número correcto en el campo `biometric_id`
- Asignar un turno al empleado

## Permisos Requeridos

El wizard requiere pertenecer al grupo: **HR Manager Custom** del módulo ZKTeco

Solo usuarios con este permiso podrán:
- Acceder al wizard de importación
- Generar reportes desde Excel
- Descargar los reportes generados

## Archivos Técnicos

- **Modelo**: `modules/zkteco_realtime_connector/models/attendance_import_wizard.py`
- **Vista**: `modules/zkteco_realtime_connector/views/attendance_import_wizard_views.xml`
- **Permisos**: `modules/zkteco_realtime_connector/security/ir.model.access.csv`

## Actualización del Módulo

Después de instalar/actualizar este componente:

```bash
python odoo-bin -u zkteco_realtime_connector -d tu_base_de_datos
```

O desde la interfaz de Odoo:
1. Ir a **Aplicaciones**
2. Buscar "zkteco_realtime_connector"
3. Hacer clic en **Actualizar**
