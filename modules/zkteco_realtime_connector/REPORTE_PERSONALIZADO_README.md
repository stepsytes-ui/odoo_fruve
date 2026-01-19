# Reporte Personalizado de Asistencia - Guía de Uso

## ¿Qué es?
Un wizard en Odoo 18 Community que permite generar reportes de asistencia en Excel con un formato personalizado.

## Características

✅ **Filtrado por rango de fechas**: Selecciona el período que deseas reportar
✅ **Filtrado opcional por empleado**: Generar reporte de todos los empleados o de uno específico
✅ **Columnas dinámicas**: Se crean automáticamente según el rango de fechas (una columna por día)
✅ **Formato inteligente**: Cada columna muestra el nombre del día y la fecha (ej: "Lunes 19")
✅ **Check-ins por hora**: Todos los check-in times del empleado ese día en formato HH:MM:SS
✅ **Información básica**: No. Empleado, Nombre, Turno en las primeras columnas
✅ **Solo visible para RH**: El botón aparece solo para usuarios del grupo de RRHH

## Cómo usar

### 1. Acceder al reporte
- Ve a **Recursos Humanos > Asistencia**
- En la vista de listado, verás el botón **"📊 Reporte Personalizado"** (solo si eres RH)

### 2. Configurar filtros
- **Fecha Desde**: Selecciona la fecha inicial del rango
- **Fecha Hasta**: Selecciona la fecha final del rango
- **Empleado (Opcional)**: 
  - Dejar vacío para generar reporte de TODOS los empleados
  - Seleccionar un empleado específico para generar solo su reporte

### 3. Generar reporte
- Haz clic en **"Generar Reporte"**
- El Excel se descargará automáticamente

## Formato del Excel

### Estructura de columnas
```
| No. Empleado | Nombre | Turno | Viernes 16 | Sábado 17 | Domingo 18 | ... |
|--------------|--------|-------|-----------|----------|-----------|-----|
| 12345        | Juan   | 7-3   | 07:55:05  | SIN REG  | 08:02:10  | ... |
|              |        |       | 12:50:00  |          | 12:58:03  |     |
|              |        |       | 13:50:00  |          | 13:55:00  |     |
|              |        |       | 16:00:10  |          | 16:05:45  |     |
```

### Interpretación
- Cada fila representa un empleado
- Las primeras 3 columnas son fijas: No. Empleado, Nombre, Turno
- Las columnas restantes corresponden a cada día del rango seleccionado
- En cada celda de día se listan todos los check-ins separados por " - "
- Si un empleado no tiene check-ins ese día, la celda aparecerá vacía

## Instalación

### Requisitos
- Odoo 18 Community
- Módulo `zkteco_realtime_connector` instalado

### Dependencias Python
Se instala automáticamente:
- `openpyxl`: Para generar archivos Excel

Si necesitas instalarlo manualmente:
```bash
pip install openpyxl
```

## Permisos

El botón **"Reporte Personalizado"** solo es visible para usuarios pertenecientes al grupo:
- `zkteco_realtime_connector.group_hr_manager_custom`

Este grupo debe estar asignado en Configuración > Usuarios.

## Validaciones

✓ Las fechas "Desde" no pueden ser posteriores a "Hasta"
✓ Si no hay empleados que cumplan los criterios, muestra un mensaje de error
✓ Solo se incluyen empleados activos con turno asignado

## Datos incluidos en el reporte

**Información del empleado:**
- Número de Empleado (biometric_id)
- Nombre completo
- Turno asignado

**Asistencias incluidas:**
- Check-ins con status: `on_time`, `late`, `LunchS`, `LunchE`, `end`, `overtime`
- No se incluyen faltas ni permisos

**Orden:**
- Las asistencias se muestran en orden cronológico por día

## Notas técnicas

- La hora se convierte automáticamente a la zona horaria local (Tijuana: America/Tijuana)
- El archivo se genera en memoria para mayor rendimiento
- Se descarga automáticamente sin necesidad de guardar manualmente
