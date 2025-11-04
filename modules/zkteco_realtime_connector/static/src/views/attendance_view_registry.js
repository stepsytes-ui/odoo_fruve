/** @odoo-module */

import { registry } from "@web/core/registry";
import { AttendanceDashboardWrapper } from "./attendance_dashboard_wrapper";

// Obtiene la vista de lista de asistencia original
const attendanceListView = registry.category("views").get("attendance_list_view");

// Sobrescribe la vista 'attendance_list_view' en el registro
registry.category("views").add("attendance_list_view", {
    ...attendanceListView, // Copia todo lo original (modelo, props, etc.)
    Controller: AttendanceDashboardWrapper, // ¡Pero reemplaza el controlador por nuestro wrapper!
}, { force: true }); // 'force: true' es clave para sobrescribir