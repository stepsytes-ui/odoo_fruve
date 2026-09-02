# -*- coding: utf-8 -*-
"""
Script para generar datos de ejemplo de movimientos de almacén
Ejecución: python -m odoo.tools.translate --no-fuzzy -c odoo.conf -d odoo18Pro
O mejor aún, ejecutar en el shell de Odoo:
    exec(open('script_generate_warehouse_movements.py').read())
"""

import random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Configuración
YEAR_START = 2025
NUM_YEARS = 2  # 2025 y 2026
MIN_MOVEMENTS_PER_MONTH = 10
MAX_MOVEMENTS_PER_MONTH = 20

# Tipos de movimiento
MOVE_TYPES = ['inicial', 'entrada', 'salida', 'transferencia']

# Obtener ambiente de Odoo
env = odoo.api.Environment.context
users = env['res.users'].search([('active', '=', True)], limit=1)
company_id = users[0].company_id.id if users else 1

# Obtener almacenes
warehouses = env['compras.warehouse'].search([])
if len(warehouses) < 2:
    print("⚠️  Se necesitan al menos 2 almacenes para crear movimientos de transferencia")
    print(f"✓ Encontrados: {len(warehouses)} almacén(es)")
else:
    print(f"✓ Encontrados: {len(warehouses)} almacén(es)")

# Obtener productos
products = env['compras.product'].search([], limit=50)
if not products:
    print("❌ No hay productos disponibles. Crea al menos 1 producto en el sistema.")
    exit()
else:
    print(f"✓ Encontrados: {len(products)} producto(s)")

# Contar movimientos existentes
existing_moves = env['compras.inventory.move'].search([])
print(f"✓ Movimientos existentes: {len(existing_moves)}")

print("\n" + "="*60)
print("GENERANDO DATOS DE EJEMPLO")
print("="*60)

# Contador de registros creados
created_count = 0
month_counter = {}

# Iterar sobre cada mes de los últimos 2 años
current_date = datetime(YEAR_START, 1, 1)
end_date = datetime.now()

while current_date <= end_date:
    month_key = current_date.strftime('%Y-%m')
    
    # Determinar cantidad de movimientos para este mes
    num_movements = random.randint(MIN_MOVEMENTS_PER_MONTH, MAX_MOVEMENTS_PER_MONTH)
    month_counter[month_key] = num_movements
    
    print(f"\n📅 Mes: {current_date.strftime('%B %Y')} → {num_movements} movimientos")
    
    # Crear movimientos para este mes
    for i in range(num_movements):
        try:
            # Fecha aleatoria dentro del mes
            random_day = random.randint(1, 28)  # Usar 28 para evitar problemas con meses cortos
            movement_date = current_date.replace(day=random_day, hour=random.randint(8, 17), minute=random.randint(0, 59))
            
            # Tipo de movimiento aleatorio
            move_type = random.choice(MOVE_TYPES)
            
            # Producto aleatorio
            product = random.choice(products)
            
            # Cantidad aleatoria
            quantity = random.randint(1, 100)
            quantity_done = quantity  # Cantidad realizada igual a solicitada
            
            # Almacenes
            if move_type == 'transferencia' and len(warehouses) >= 2:
                source_warehouse = random.choice(warehouses)
                # Elegir almacén diferente para destino
                destination_warehouse = random.choice([w for w in warehouses if w.id != source_warehouse.id])
            elif move_type == 'entrada':
                source_warehouse = None
                destination_warehouse = random.choice(warehouses)
            elif move_type == 'salida':
                source_warehouse = random.choice(warehouses)
                destination_warehouse = None
            else:  # inicial
                source_warehouse = None
                destination_warehouse = random.choice(warehouses)
            
            # Crear movimiento
            move_vals = {
                'company_id': company_id,
                'destination_company_id': company_id,
                'movement_date': movement_date,
                'move_type': move_type,
                'product_id': product.id,
                'quantity': quantity,
                'quantity_done': quantity_done,
                'source_warehouse_id': source_warehouse.id if source_warehouse else None,
                'destination_warehouse_id': destination_warehouse.id if destination_warehouse else None,
            }
            
            # Crear el registro
            env['compras.inventory.move'].create(move_vals)
            created_count += 1
            
        except Exception as e:
            print(f"  ⚠️  Error creando movimiento {i+1}: {str(e)}")
            continue
    
    # Avanzar al siguiente mes
    current_date = current_date + relativedelta(months=1)

print("\n" + "="*60)
print("RESUMEN DE GENERACIÓN")
print("="*60)
print(f"✅ Movimientos creados: {created_count}")
print(f"✅ Meses procesados: {len(month_counter)}")
print(f"✅ Movimientos totales en sistema: {len(env['compras.inventory.move'].search([]))}")

print("\n📊 Desglose por mes:")
for month, count in sorted(month_counter.items()):
    print(f"  {month}: {count} movimientos")

print("\n✅ ¡Script completado exitosamente!")
print("\nAhora puedes ir a: Compras → Almacén → Reportes")
print("Y generar gráficas con los datos de ejemplo.")
