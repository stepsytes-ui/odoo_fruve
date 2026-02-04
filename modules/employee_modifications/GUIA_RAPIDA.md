# 🚀 Guía Rápida: Importar CURP y RFC

## 📝 Preparar el Excel

Tu archivo debe tener **4 columnas** en este orden:

| A | B | C | D |
|---|---|---|---|
| **Número de Empleado** | **Nombre** | **CURP** | **RFC** |
| 1001 | Juan Pérez | PEGJ850101HDFRNN05 | PEGJ850101ABC |
| 1002 | María López | LOHM900215MDFRNN08 | LOHM900215XY1 |

### ⚠️ Importante:
- Primera fila = Encabezados (se omite automáticamente)
- Número de Empleado = debe coincidir con el campo en Odoo
- CURP = exactamente 18 caracteres
- RFC = 12 o 13 caracteres

## 🔄 Actualizar el Módulo

```bash
# Reiniciar Odoo y actualizar
python odoo-bin -u employee_modifications -d tu_base_datos
```

O desde la interfaz:
**Aplicaciones** → Buscar "employee_modifications" → **Actualizar**

## 📤 Importar Datos

### Método 1: Desde el Menú
**Empleados** → **Importar CURP y RFC** → Seleccionar Excel → **Importar**

### Método 2: Desde Lista de Empleados  
**Empleados** → **Acción** → **Importar CURP y RFC**

## ✅ Ver Resultados

Después de importar verás:
- ✅ Empleados actualizados
- ⚠️ Empleados no encontrados
- ❌ Errores de validación

## 👀 Ver CURP y RFC

**Empleados** → [Seleccionar empleado] → **Información Privada** → Sección "Identificación"

Ahí encontrarás:
- **CURP**: Campo editable (Identification No)
- **RFC**: Campo editable directo

## 🎯 Ejemplo Excel

Ya tienes un archivo de ejemplo listo:
`ejemplo_importacion_curp_rfc.xls`

O genera uno nuevo:
```bash
python modules/employee_modifications/generar_ejemplo_excel.py
```

## ❓ ¿Problemas?

### "Empleado no encontrado"
→ Verifica que el Número de Empleado coincida con el campo `biometric_id` en Odoo

### "CURP inválido"
→ Debe tener exactamente 18 caracteres (sin espacios)

### "RFC inválido"  
→ Debe tener 12 o 13 caracteres (sin espacios)

### "Error al leer Excel"
→ Asegúrate de que sea un archivo .xls o .xlsx válido

---

📖 **Documentación completa**: Ver `IMPORTACION_CURP_RFC.md`
