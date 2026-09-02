# -*- coding: utf-8 -*-

import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WarehouseGenerateSampleData(models.TransientModel):
    _name = 'warehouse.generate.sample.data'
    _description = 'Generar Datos de Ejemplo de Movimientos de Almacén'

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    start_year = fields.Integer(
        string='Año Inicial',
        required=True,
        default=2025,
        help='Año desde el cual empezar a generar movimientos',
    )

    num_months = fields.Integer(
        string='Cantidad de Meses',
        required=True,
        default=12,
        help='Cantidad de meses a partir del año inicial a generar',
    )

    min_movements_per_month = fields.Integer(
        string='Mínimo de Movimientos por Mes',
        required=True,
        default=10,
    )

    max_movements_per_month = fields.Integer(
        string='Máximo de Movimientos por Mes',
        required=True,
        default=25,
    )

    include_inicial = fields.Boolean(
        string='Incluir Inventario Inicial',
        default=True,
    )

    include_entrada = fields.Boolean(
        string='Incluir Entradas',
        default=True,
    )

    include_salida = fields.Boolean(
        string='Incluir Salidas',
        default=True,
    )

    include_transferencia = fields.Boolean(
        string='Incluir Transferencias',
        default=True,
    )

    @api.constrains('start_year', 'num_months', 'min_movements_per_month', 'max_movements_per_month')
    def _check_values(self):
        for record in self:
            if record.start_year < 2000 or record.start_year > datetime.now().year:
                raise ValidationError(_('El año inicial debe ser entre 2000 y el año actual'))
            
            if record.num_months < 1 or record.num_months > 120:
                raise ValidationError(_('La cantidad de meses debe estar entre 1 y 120'))
            
            if record.min_movements_per_month < 1:
                raise ValidationError(_('El mínimo de movimientos debe ser al menos 1'))
            
            if record.max_movements_per_month < record.min_movements_per_month:
                raise ValidationError(_('El máximo no puede ser menor que el mínimo'))

    def action_generate_data(self):
        """Genera datos de ejemplo de movimientos de almacén"""
        self.ensure_one()

        # Validar que existan almacenes y productos
        warehouses = self.env['compras.warehouse'].search([('company_id', '=', self.company_id.id)])
        products = self.env['compras.product'].search([('company_id', '=', self.company_id.id)], limit=100)

        if not warehouses:
            raise ValidationError(_('No hay almacenes disponibles en la empresa. Crea al menos 1 almacén.'))
        
        if not products:
            raise ValidationError(_('No hay productos disponibles en la empresa. Crea al menos 1 producto.'))

        # Obtener tipos de movimiento seleccionados
        move_types = []
        if self.include_inicial:
            move_types.append('inicial')
        if self.include_entrada:
            move_types.append('entrada')
        if self.include_salida:
            move_types.append('salida')
        if self.include_transferencia:
            move_types.append('transferencia')

        if not move_types:
            raise ValidationError(_('Debes seleccionar al menos un tipo de movimiento'))

        # Generar movimientos
        created_count = 0
        current_date = datetime(self.start_year, 1, 1)
        end_date = current_date + relativedelta(months=self.num_months - 1)
        
        InventoryMove = self.env['compras.inventory.move']

        while current_date <= end_date:
            # Cantidad de movimientos para este mes
            num_movements = random.randint(
                self.min_movements_per_month,
                self.max_movements_per_month
            )

            # Crear movimientos para este mes
            for movement_index in range(num_movements):
                try:
                    # Fecha aleatoria dentro del mes
                    random_day = random.randint(1, 28)
                    random_hour = random.randint(8, 18)
                    random_minute = random.randint(0, 59)
                    
                    movement_date = current_date.replace(
                        day=random_day,
                        hour=random_hour,
                        minute=random_minute
                    )

                    # Tipo de movimiento aleatorio
                    move_type = random.choice(move_types)

                    # Producto aleatorio
                    product = random.choice(products)

                    # Cantidad aleatoria
                    quantity = random.randint(5, 200)

                    # Determinar almacenes según tipo de movimiento
                    if move_type == 'transferencia':
                        if len(warehouses) < 2:
                            # Si no hay 2 almacenes, usar salida
                            move_type = 'salida'
                            source_warehouse = warehouses[0]
                            destination_warehouse = None
                        else:
                            source_warehouse = random.choice(warehouses)
                            destination_warehouse = random.choice(
                                [w for w in warehouses if w.id != source_warehouse.id]
                            )
                    elif move_type == 'entrada':
                        source_warehouse = None
                        destination_warehouse = random.choice(warehouses)
                    elif move_type == 'salida':
                        source_warehouse = random.choice(warehouses)
                        destination_warehouse = None
                    else:  # inicial
                        source_warehouse = None
                        destination_warehouse = random.choice(warehouses)

                    # Crear el movimiento
                    InventoryMove.create({
                        'company_id': self.company_id.id,
                        'destination_company_id': self.company_id.id,
                        'movement_date': movement_date,
                        'move_type': move_type,
                        'product_id': product.id,
                        'quantity': quantity,
                        'quantity_done': quantity,
                        'source_warehouse_id': source_warehouse.id if source_warehouse else None,
                        'destination_warehouse_id': destination_warehouse.id if destination_warehouse else None,
                    })
                    
                    created_count += 1

                except Exception as e:
                    # Registrar error pero continuar
                    continue

            # Avanzar al siguiente mes
            current_date = current_date + relativedelta(months=1)

        # Mostrar mensaje de éxito
        message = (
            f'✅ Datos de ejemplo generados exitosamente!\n\n'
            f'Movimientos creados: {created_count}\n'
            f'Período: {self.start_year}-01-01 a {end_date.strftime("%Y-%m-%d")}\n'
            f'Almacenes: {len(warehouses)}\n'
            f'Productos: {len(products)}\n\n'
            f'Ahora puedes ver los datos en:\n'
            f'Compras → Almacén → Reportes'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Generación Completada'),
                'message': message,
                'type': 'success',
                'sticky': True,
            },
        }
