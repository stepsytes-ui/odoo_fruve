/** @odoo-module */

console.log("--- 1. main.js FUE LEÍDO POR EL NAVEGADOR ---");

import { registry } from "@web/core/registry";
import { AttendanceDashboard } from "./components/attendance_dashboard";

console.log("--- 2. main.js IMPORTACIONES COMPLETADAS ---");

const actionRegistry = registry.category("actions");
actionRegistry.add("hr_attendance_dashboard.dashboard", AttendanceDashboard);

console.log("--- 3. main.js ACCIÓN REGISTRADA ---");