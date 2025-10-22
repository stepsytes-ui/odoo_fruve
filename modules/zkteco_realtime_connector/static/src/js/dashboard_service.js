/** @odoo-module **/

import { registry } from "@web/core/registry";
import { http } from "@web/core/network/http_service";

/**
 * Servicio de Dashboard de Asistencia
 *
 * Este servicio actúa como un puente limpio entre los componentes
 * de Owl y el controlador de Python.
 */
const attendanceDashboardService = {
    dependencies: ["http"], // Declaramos que necesitamos el servicio HTTP
    
    /**
     * @param {Object} env El entorno de Odoo
     * @param {Object} services Servicios inyectados
     */
    start(env, { http }) {
        
        // --- CORRECCIÓN AQUÍ ---
        // Debes retornar un objeto que contenga las funciones.
        return {
            
            // Función para obtener los KPIs
            getKPIs() {
                return http.post("/attendance/dashboard/get_kpis", {});
            },

            // Función para obtener las Listas
            getLists() {
                return http.post("/attendance/dashboard/get_lists", {});
            },

            // Función para obtener los datos del gráfico
            getChartData() {
                return http.post("/attendance/dashboard/get_chart_data", {});
            },
        }; 
    },
};

// Registramos el servicio en Odoo para que 'useService' pueda encontrarlo
registry.category("services").add("attendanceDashboardService", attendanceDashboardService);