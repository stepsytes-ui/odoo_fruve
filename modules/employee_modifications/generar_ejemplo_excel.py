#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar un archivo Excel de ejemplo para importar CURP y RFC
"""

import xlwt
import os

# Crear un nuevo workbook
workbook = xlwt.Workbook(encoding='utf-8')
sheet = workbook.add_sheet('Empleados')

# Estilos
header_style = xlwt.XFStyle()
header_font = xlwt.Font()
header_font.bold = True
header_font.height = 240
header_style.font = header_font

# Patrón de fondo para encabezados
pattern = xlwt.Pattern()
pattern.pattern = xlwt.Pattern.SOLID_PATTERN
pattern.pattern_fore_colour = xlwt.Style.colour_map['gray25']
header_style.pattern = pattern

# Alineación
alignment = xlwt.Alignment()
alignment.horz = xlwt.Alignment.HORZ_CENTER
alignment.vert = xlwt.Alignment.VERT_CENTER
header_style.alignment = alignment

# Escribir encabezados
headers = ['Número de Empleado', 'Nombre del Empleado', 'CURP', 'RFC']
for col, header in enumerate(headers):
    sheet.write(0, col, header, header_style)

# Ajustar ancho de columnas
sheet.col(0).width = 5000  # Número de Empleado
sheet.col(1).width = 8000  # Nombre del Empleado
sheet.col(2).width = 6000  # CURP
sheet.col(3).width = 5000  # RFC

# Datos de ejemplo
datos_ejemplo = [
    ['1001', 'Juan Pérez García', 'PEGJ850101HDFRNN05', 'PEGJ850101ABC'],
    ['1002', 'María López Hernández', 'LOHM900215MDFRNN08', 'LOHM900215XY1'],
    ['1003', 'Carlos Rodríguez Martínez', 'ROMC750512HDFRNN03', 'ROMC750512AB2'],
    ['1004', 'Ana Martínez Sánchez', 'MASA881120MDFRNN04', 'MASA881120CD3'],
    ['1005', 'Luis González Torres', 'GOTL920305HDFRNN09', 'GOTL920305EF4'],
]

# Estilo para datos
data_style = xlwt.XFStyle()
data_font = xlwt.Font()
data_font.height = 200
data_style.font = data_font

# Escribir datos de ejemplo
for row, data in enumerate(datos_ejemplo, start=1):
    for col, value in enumerate(data):
        sheet.write(row, col, value, data_style)

# Guardar el archivo
output_path = os.path.join(os.path.dirname(__file__), 'ejemplo_importacion_curp_rfc.xls')
workbook.save(output_path)

print(f"✅ Archivo de ejemplo creado exitosamente: {output_path}")
print("\nEstructura del archivo:")
print("- Columna A: Número de Empleado (biometric_id)")
print("- Columna B: Nombre del Empleado")
print("- Columna C: CURP (18 caracteres)")
print("- Columna D: RFC (12 o 13 caracteres)")
print("\nEl archivo contiene 5 registros de ejemplo.")
