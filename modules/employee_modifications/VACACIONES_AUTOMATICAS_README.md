# Acción Automática: Recalculación de Vacaciones Anuales

## Descripción General

Esta acción automática (cron) detecta cuando un empleado ha cumplido un año más de antigüedad desde su última renovación de vacaciones y recalcula automáticamente sus días de vacaciones disponibles.

## Características Principales

### 1. Vacaciones NO Acumulables
- Cuando un empleado cumple un año más, sus vacaciones se **renuevan completamente**
- Los días utilizados se resetean a 0
- Los días disponibles se recalculan según la nueva antigüedad
- Los **ajustes manuales** (`dias_vacaciones_ajuste`) se mantienen

### 2. Tabla de Vacaciones por Antigüedad

| Años de Antigüedad | Días de Vacaciones |
|-------------------|-------------------|
| 1 año             | 12 días           |
| 2 años            | 14 días           |
| 3 años            | 16 días           |
| 4 años            | 18 días           |
| 5 años            | 20 días           |
| 6-10 años         | 22 días           |
| 11-15 años        | 24 días           |
| 16-20 años        | 26 días           |
| 21-25 años        | 28 días           |
| 26-30 años        | 30 días           |
| 31-35 años        | 32 días           |

## Funcionamiento Técnico

### Ejecución del Cron
- **Frecuencia**: Se ejecuta automáticamente cada día
- **Hora**: Según la configuración del servidor (por defecto, medianoche)
- **Modelo**: `employee.expedient`
- **Método**: `_cron_recalcular_vacaciones_anuales()`

### Lógica de Renovación

1. **Busca expedientes elegibles**:
   - Empleados activos
   - Estado: 'activo'
   - Tipo de registro: 'alta' o 'reingreso'

2. **Verifica antigüedad**:
   - Compara la fecha actual con `fecha_ultima_renovacion` (o `fecha_movimiento` si es la primera renovación)
   - Si han pasado 12 meses completos, procede con la renovación

3. **Actualiza el expediente**:
   - Calcula la nueva antigüedad total
   - Busca los días de vacaciones según la tabla
   - Resetea `dias_vacaciones_utilizados` a 0
   - Actualiza `fecha_ultima_renovacion` a la fecha actual
   - Recalcula campos computados

4. **Registra la acción**:
   - Crea un mensaje en el chatter del expediente
   - Registra log en el servidor

## Campos Nuevos Agregados

### `fecha_ultima_renovacion` (Date)
- **Descripción**: Fecha en que se renovaron las vacaciones por última vez
- **Uso**: El sistema usa este campo para determinar cuándo hacer la próxima renovación
- **Visible en**: Pestaña "Cálculo de Vacaciones" → Grupo "Estado de Antigüedad"
- **Comportamiento**: 
  - Se actualiza automáticamente cuando el cron ejecuta la renovación
  - Si está vacío, el sistema usa `fecha_movimiento` como referencia

## Configuración y Administración

### Activar/Desactivar el Cron

1. Ir a **Ajustes** → **Técnico** → **Automatización** → **Acciones Programadas**
2. Buscar: "Recalcular Vacaciones Anuales"
3. Marcar/desmarcar el campo **Activo**

### Modificar la Frecuencia

En el registro del cron, puedes modificar:
- **Intervalo**: Número (ejemplo: 1)
- **Unidad**: días, semanas, meses, etc.

**Nota**: Se recomienda mantener la ejecución diaria para asegurar que las renovaciones se realicen puntualmente.

### Ejecutar Manualmente

Para probar o forzar una ejecución:
1. Ir al registro del cron "Recalcular Vacaciones Anuales"
2. Hacer clic en el botón **"Ejecutar Manualmente"**
3. Revisar los logs del servidor para ver cuántos expedientes se actualizaron

## Ejemplo de Uso

### Caso 1: Empleado con 1 año cumplido

**Antes**:
- Fecha de alta: 10/02/2025
- Antigüedad: 1 año, 0 meses
- Días de vacaciones ley: 12
- Días utilizados: 8
- Días disponibles: 4
- Última renovación: (vacío)

**Después del cron (11/02/2026)**:
- Antigüedad: 1 año, 0 meses
- Días de vacaciones ley: 12
- Días utilizados: 0 ← **RESETEADO**
- Días disponibles: 12 ← **RENOVADO**
- Última renovación: 11/02/2026

### Caso 2: Empleado con 5 años que pasa a 6

**Antes**:
- Fecha de alta: 10/02/2020
- Antigüedad: 5 años, 11 meses
- Días de vacaciones ley: 20
- Días utilizados: 15
- Días disponibles: 5

**Después del cron (11/02/2026)**:
- Antigüedad: 6 años, 0 meses
- Días de vacaciones ley: 22 ← **AUMENTADO**
- Días utilizados: 0 ← **RESETEADO**
- Días disponibles: 22 ← **RENOVADO CON MÁS DÍAS**

## Monitoreo y Logs

### Mensajes en el Chatter
Cada renovación genera un mensaje automático en el expediente:
```
Renovación automática de vacaciones: El empleado ha cumplido un año más.
Antigüedad: 6 años. Nuevos días de vacaciones: 22 días.
```

### Logs del Servidor
En los logs de Odoo verás mensajes como:
```
Cron de vacaciones ejecutado: 5 expedientes actualizados
```

## Consideraciones Importantes

1. **Ajustes Manuales**: Los valores en `dias_vacaciones_ajuste` se mantienen y se suman a los días de ley.

2. **Empleados Inactivos**: Solo se procesan empleados con estado 'activo'.

3. **Múltiples Compañías**: El sistema respeta la configuración multicompañía.

4. **Primer Año**: La primera renovación ocurre exactamente 1 año después de la fecha de movimiento (alta o reingreso).

5. **Años Siguientes**: Las renovaciones subsecuentes se basan en `fecha_ultima_renovacion`.

## Solución de Problemas

### El cron no está ejecutándose
- Verificar que el cron esté activo
- Revisar que el servicio de Odoo esté corriendo
- Verificar logs del servidor para errores

### No se actualizaron vacaciones esperadas
- Verificar que el empleado esté activo
- Confirmar que ha pasado al menos 1 año completo
- Revisar el campo `fecha_ultima_renovacion`

### Vacaciones incorrectas después de renovación
- Verificar la tabla de vacaciones en el código
- Revisar ajustes manuales aplicados
- Comprobar el cálculo de antigüedad

## Archivos Relacionados

- **Modelo**: `modules/employee_modifications/models/employee_expedient.py`
- **Cron**: `modules/employee_modifications/data/vacation_renewal_cron.xml`
- **Vista**: `modules/employee_modifications/views/employee_expedient.xml`
- **Manifest**: `modules/employee_modifications/__manifest__.py`

## Actualización del Módulo

Después de instalar estos cambios, debes actualizar el módulo:

```bash
python odoo-bin -u employee_modifications -d nombre_base_de_datos
```

O desde la interfaz:
1. Ir a **Aplicaciones**
2. Buscar "employee_modifications"
3. Hacer clic en **Actualizar**
