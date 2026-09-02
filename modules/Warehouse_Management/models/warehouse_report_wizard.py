# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WarehouseReportWizard(models.TransientModel):
    _name = 'warehouse.report.wizard'
    _description = 'Wizard para Generar Reportes de Almacén'

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    report_type = fields.Selection(
        [
            ('movement_by_warehouse', 'Movimientos por Almacén'),
            ('movement_by_product', 'Movimientos por Producto'),
            ('inventory_summary', 'Resumen de Inventario'),
        ],
        string='Tipo de Reporte',
        default='movement_by_warehouse',
        required=True,
    )

    period_mode = fields.Selection(
        [
            ('range', 'Rango de fechas'),
            ('month', 'Este mes'),
            ('quarter', 'Este trimestre'),
            ('year', 'Este año'),
        ],
        string='Período',
        required=True,
        default='range',
    )

    date_from = fields.Date(
        string='Fecha Desde',
        required=True,
        default=lambda self: fields.Date.context_today(self) - timedelta(days=30),
    )

    date_to = fields.Date(
        string='Fecha Hasta',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )

    grouping_period = fields.Selection(
        [
            ('day', 'Por Día'),
            ('week', 'Por Semana'),
            ('month', 'Por Mes'),
            ('quarter', 'Por Trimestre'),
            ('year', 'Por Año'),
        ],
        string='Agrupar por',
        required=True,
        default='month',
    )

    warehouse_ids = fields.Many2many(
        'compras.warehouse',
        'warehouse_report_wizard_warehouse_rel',
        'wizard_id',
        'warehouse_id',
        string='Almacenes',
        domain="[('company_id', '=', company_id)]",
    )

    move_type_ids = fields.Many2many(
        'compras.move.type',
        'warehouse_report_wizard_movetype_rel',
        'wizard_id',
        'movetype_id',
        string='Tipos de Movimiento',
    )

    show_chart_type = fields.Selection(
        [
            ('bar', 'Gráfica de Barras'),
            ('line', 'Gráfica de Líneas'),
            ('pie', 'Gráfica de Pastel'),
            ('area', 'Gráfica de Área'),
        ],
        string='Tipo de Gráfica',
        default='bar',
        required=True,
    )

    @api.onchange('period_mode')
    def _onchange_period_mode(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.period_mode == 'range':
                record.date_from = today - timedelta(days=30)
                record.date_to = today
            elif record.period_mode == 'month':
                record.date_from = today.replace(day=1)
                record.date_to = (today.replace(day=1) + relativedelta(months=1) - timedelta(days=1))
            elif record.period_mode == 'quarter':
                quarter = (today.month - 1) // 3
                quarter_start = today.replace(month=quarter * 3 + 1, day=1)
                quarter_end = quarter_start + relativedelta(months=3) - timedelta(days=1)
                record.date_from = quarter_start
                record.date_to = quarter_end
            elif record.period_mode == 'year':
                record.date_from = today.replace(month=1, day=1)
                record.date_to = today.replace(month=12, day=31)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError(
                    _('La fecha "Desde" no puede ser posterior a la fecha "Hasta"')
                )

    def action_view_report(self):
        """Abre la vista previa del reporte en una nueva pestaña"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/warehouse/report/preview?wizard_id={self.id}',
            'target': 'new',
        }

    def _get_period_label(self, date_value):
        """Genera etiqueta para un período según grouping_period"""
        self.ensure_one()
        months = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        
        if self.grouping_period == 'day':
            return date_value.strftime('%d/%m/%Y')
        elif self.grouping_period == 'week':
            week_start = date_value - timedelta(days=date_value.weekday())
            week_end = week_start + timedelta(days=6)
            return f"Semana {week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}"
        elif self.grouping_period == 'month':
            month_name = months.get(date_value.month, '')
            return f"{month_name} {date_value.year}"
        elif self.grouping_period == 'quarter':
            quarter = (date_value.month - 1) // 3 + 1
            return f"Q{quarter} {date_value.year}"
        elif self.grouping_period == 'year':
            return str(date_value.year)

    def _get_period_key(self, date_value):
        """Genera clave única para agrupar por período"""
        if self.grouping_period == 'day':
            return date_value.strftime('%Y-%m-%d')
        elif self.grouping_period == 'week':
            week_start = date_value - timedelta(days=date_value.weekday())
            return week_start.strftime('%Y-W%V')
        elif self.grouping_period == 'month':
            return date_value.strftime('%Y-%m')
        elif self.grouping_period == 'quarter':
            quarter = (date_value.month - 1) // 3 + 1
            return f"{date_value.year}-Q{quarter}"
        elif self.grouping_period == 'year':
            return str(date_value.year)

    def _get_movement_data_by_warehouse(self):
        """Genera datos de movimientos agrupados por almacén y período"""
        self.ensure_one()

        InventoryMove = self.env['compras.inventory.move']
        
        # Convertir fechas a datetime para la consulta
        date_from_dt = fields.Datetime.to_datetime(self.date_from)
        date_to_dt = fields.Datetime.to_datetime(self.date_to) + timedelta(days=1)
        
        domain = [
            ('company_id', '=', self.company_id.id),
            ('movement_date', '>=', date_from_dt),
            ('movement_date', '<', date_to_dt),
        ]

        if self.warehouse_ids:
            domain += [
                '|',
                ('source_warehouse_id', 'in', self.warehouse_ids.ids),
                ('destination_warehouse_id', 'in', self.warehouse_ids.ids),
            ]

        if self.move_type_ids:
            # Obtener códigos de los tipos de movimiento seleccionados
            move_type_codes = self.move_type_ids.mapped('code')
            domain.append(('move_type', 'in', move_type_codes))

        moves = InventoryMove.search(domain)

        # Estructura: {warehouse_name: {period_key: {entrada: qty, salida: qty, ...}}}
        data_structure = {}
        selected_warehouse_ids = set(self.warehouse_ids.ids)

        for move in moves:
            warehouse_names = set()

            def include_warehouse(warehouse):
                return warehouse and (
                    not selected_warehouse_ids or warehouse.id in selected_warehouse_ids
                )

            if move.move_type == 'entrada':
                if include_warehouse(move.destination_warehouse_id):
                    warehouse_names.add(move.destination_warehouse_id.name)
            elif move.move_type == 'salida':
                if include_warehouse(move.source_warehouse_id):
                    warehouse_names.add(move.source_warehouse_id.name)
            elif move.move_type == 'transferencia':
                if include_warehouse(move.source_warehouse_id):
                    warehouse_names.add(f"{move.source_warehouse_id.name} (Salida)")
                if include_warehouse(move.destination_warehouse_id):
                    warehouse_names.add(f"{move.destination_warehouse_id.name} (Entrada)")
            else:
                if include_warehouse(move.destination_warehouse_id):
                    warehouse_names.add(move.destination_warehouse_id.name)

            # Convertir datetime a fecha para obtener period_key
            move_date = fields.Datetime.from_string(move.movement_date).date() if isinstance(move.movement_date, str) else move.movement_date.date()
            period_key = self._get_period_key(move_date)

            for warehouse_name in warehouse_names:
                if warehouse_name not in data_structure:
                    data_structure[warehouse_name] = {}

                if period_key not in data_structure[warehouse_name]:
                    data_structure[warehouse_name][period_key] = {
                        'period_label': self._get_period_label(move_date),
                        'entrada': 0,
                        'salida': 0,
                        'transferencia': 0,
                        'inicial': 0,
                    }

                # Usar quantity_done si existe, sino quantity
                qty = move.quantity_done if move.quantity_done else move.quantity
                data_structure[warehouse_name][period_key][move.move_type] += qty

        return data_structure

    def _build_preview_html(self):
        """Construye HTML para la vista previa del reporte"""
        self.ensure_one()

        if self.report_type == 'movement_by_warehouse':
            data = self._get_movement_data_by_warehouse()
            html_content = self._build_warehouse_movement_html(data)
        else:
            html_content = '<p>Tipo de reporte no implementado aún.</p>'

        return html_content

    def _build_warehouse_movement_html(self, data):
        """Construye HTML específico para reporte de movimientos por almacén"""
        html = '''
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Reporte de Movimientos de Almacén</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                .header h1 {
                    margin: 0;
                    color: #333;
                }
                .header p {
                    margin: 5px 0;
                    color: #666;
                }
                .chart-container {
                    background-color: white;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                .chart-container h2 {
                    margin-top: 0;
                    color: #333;
                    border-bottom: 2px solid #007bff;
                    padding-bottom: 10px;
                }
                .chart-wrapper {
                    position: relative;
                    height: 400px;
                    margin: 20px 0;
                }
                .stats {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    margin-top: 20px;
                }
                .stat-card {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }
                .stat-card.entrada { background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%); color: #333; }
                .stat-card.salida { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: #333; }
                .stat-card.transferencia { background: linear-gradient(135deg, #30cfd0 0%, #330867 100%); }
                .stat-card h3 {
                    margin: 0;
                    font-size: 14px;
                    text-transform: uppercase;
                    opacity: 0.9;
                }
                .stat-card .value {
                    font-size: 32px;
                    font-weight: bold;
                    margin-top: 10px;
                }
            </style>
        </head>
        <body>
        '''

        html += f'''
        <div class="header">
            <h1>Reporte de Movimientos de Almacén</h1>
            <p><strong>Empresa:</strong> {self.company_id.name}</p>
            <p><strong>Período:</strong> {self.date_from.strftime('%d/%m/%Y')} - {self.date_to.strftime('%d/%m/%Y')}</p>
            <p><strong>Generado:</strong> {fields.Datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>
        '''

        if not data:
            html += '<p style="text-align: center; color: #999;">No hay datos para mostrar con los filtros seleccionados.</p>'
        else:
            # Crear gráfica para cada almacén
            for idx, (warehouse_name, periods_data) in enumerate(data.items()):
                sorted_periods = sorted(periods_data.items())

                # Calcular totales
                total_entrada = sum(p.get('entrada', 0) for _, p in sorted_periods)
                total_salida = sum(p.get('salida', 0) for _, p in sorted_periods)
                total_transferencia = sum(p.get('transferencia', 0) for _, p in sorted_periods)

                html += f'''
                <div class="chart-container">
                    <h2>Almacén: {warehouse_name}</h2>
                    
                    <div class="stats">
                        <div class="stat-card entrada">
                            <h3>Entradas</h3>
                            <div class="value">{total_entrada}</div>
                        </div>
                        <div class="stat-card salida">
                            <h3>Salidas</h3>
                            <div class="value">{total_salida}</div>
                        </div>
                        <div class="stat-card transferencia">
                            <h3>Transferencias</h3>
                            <div class="value">{total_transferencia}</div>
                        </div>
                    </div>

                    <div class="chart-wrapper">
                        <canvas id="chart-{idx}"></canvas>
                    </div>
                </div>
                '''

                # Preparar datos para Chart.js
                periods_labels = [p['period_label'] for _, p in sorted_periods]
                entrada_data = [p.get('entrada', 0) for _, p in sorted_periods]
                salida_data = [p.get('salida', 0) for _, p in sorted_periods]
                transferencia_data = [p.get('transferencia', 0) for _, p in sorted_periods]

                chart_type = self.show_chart_type if self.show_chart_type != 'pie' else 'bar'

                chart_config = {
                    'type': chart_type,
                    'data': {
                        'labels': periods_labels,
                        'datasets': [
                            {
                                'label': 'Entradas',
                                'data': entrada_data,
                                'backgroundColor': '#84fab0',
                                'borderColor': '#84fab0',
                                'borderWidth': 2,
                            },
                            {
                                'label': 'Salidas',
                                'data': salida_data,
                                'backgroundColor': '#fa709a',
                                'borderColor': '#fa709a',
                                'borderWidth': 2,
                            },
                            {
                                'label': 'Transferencias',
                                'data': transferencia_data,
                                'backgroundColor': '#30cfd0',
                                'borderColor': '#30cfd0',
                                'borderWidth': 2,
                            },
                        ]
                    },
                    'options': {
                        'responsive': True,
                        'maintainAspectRatio': False,
                        'plugins': {
                            'legend': {'display': True},
                            'title': {'display': False},
                        },
                        'scales': {
                            'y': {'beginAtZero': True},
                        },
                    }
                }

                html += f'''
                <script>
                    const ctx = document.getElementById('chart-{idx}').getContext('2d');
                    const config = {json.dumps(chart_config)};
                    new Chart(ctx, config);
                </script>
                '''

        html += '''
        </body>
        </html>
        '''

        return html
