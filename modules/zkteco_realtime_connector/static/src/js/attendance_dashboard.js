/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class AttendanceDashboard extends Component {
    static template = "zkteco_realtime_connector.AttendanceDashboard"; // Enlace a la plantilla QWeb
    
    setup() {
        // Servicios que usaremos
        this.dashboardService = useService("attendanceDashboardService");
        this.actionService = useService("action");

        // Referencia al <canvas> en el QWeb para dibujar el gráfico
        this.chartRef = useRef("chartCanvas");

        // El 'estado' (state) es reactivo. Cuando cambie, la vista se actualiza.
        this.state = useState({
            kpis: {
                total_employees: 0,
                total_present: 0,
                total_absent: 0,
            },
            lists: {
                last_5_records: [],
                lates_today: [],
            },
            chart: {
                labels: [],
                data: [],
            },
        });

        // onWillStart se ejecuta ANTES de que el componente se muestre.
        // Perfecto para cargar datos.
        onWillStart(async () => {
            await this.loadDashboardData();
        });

        // onMounted se ejecuta DESPUÉS de que el componente se muestre.
        // Perfecto para inicializar librerías (como Chart.js)
        onMounted(() => {
            this.renderChart();
        });
    }

    /**
     * Carga todos los datos del backend
     */
    async loadDashboardData() {
        // Usamos nuestro servicio para llamar al controlador
        const kpis = await this.dashboardService.getKPIs();
        const lists = await this.dashboardService.getLists();
        const chartData = await this.dashboardService.getChartData();

        // Actualizamos el estado, lo que refrescará la vista
        this.state.kpis = kpis;
        this.state.lists = lists;
        this.state.chart.labels = chartData.labels;
        this.state.chart.data = chartData.data;
    }

    /**
     * Dibuja el gráfico de pastel usando Chart.js (que Odoo ya incluye)
     */
    renderChart() {
        if (this.chartInstance) {
            this.chartInstance.destroy(); // Destruir gráfico anterior si existe
        }
        
        const ctx = this.chartRef.el.getContext('2d');
        this.chartInstance = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: this.state.chart.labels,
                datasets: [{
                    label: 'Ausencias por Depto.',
                    data: this.state.chart.data,
                    backgroundColor: [ // Colores de ejemplo
                        '#36A2EB', // Azul
                        '#FF6384', // Rosa
                        '#FFCE56', // Naranja
                        '#4BC0C0', // Turquesa
                        '#9966FF', // Morado
                    ],
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                }
            }
        });
    }

    /**
     * Funciones para hacer clic en las tarjetas KPI (¡Bonus!)
     */
    openEmployees() {
        this.actionService.doAction("hr.open_view_employee_list_my");
    }
    
    openPresent() {
        // Abre las asistencias de hoy que SÍ checaron
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Empleados Presentes Hoy',
            res_model: 'hr.attendance',
            views: [[false, 'list'], [false, 'form']],
            domain: [['punctuality_status', 'in', ['on_time', 'late']]], // ¡Falta añadir el dominio de fecha!
        });
    }

    openAbsent() {
        // Abre las asistencias marcadas como 'absence'
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Empleados Ausentes Hoy',
            res_model: 'hr.attendance',
            views: [[false, 'list'], [false, 'form']],
            domain: [['punctuality_status', '=', 'absence']], // ¡Falta añadir el dominio de fecha!
        });
    }
}

// Registramos el componente como una "Acción de Cliente"
registry.category("actions").add("attendance_dashboard_action", AttendanceDashboard);