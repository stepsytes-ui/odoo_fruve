/** @odoo-module */

// Hooks de Owl
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

// Definimos la clase de nuestro componente
export class AttendanceDashboard extends Component {
    static template = "hr_attendance_dashboard.AttendanceDashboard"; // Enlazamos al XML

    setup() {
        // Ahora 'useService' funcionará porque 'Component' viene
        // del core de Odoo y ya tiene el 'env' (entorno).
        this.orm = useService("orm");

        this.state = useState({
            userName: "",
            attendanceCount: 0,
            loading: true, // Añadimos un estado de carga
        });

        onWillStart(async () => {
            // Saludamos al usuario
            this.state.userName = session.userName;
            
            // Hacemos la llamada RPC (Remote Procedure Call)
            const recordCount = await this.orm.searchCount(
                "hr.attendance",
                [],

            );
            
            // Actualizamos el estado
            this.state.attendanceCount = recordCount;
            this.state.loading = false; // Terminamos de cargar
        });
    }

    // Método para el botón de refrescar (opcional pero bueno)
    async _onRefreshClick() {
        this.state.loading = true;
        try {
            const recordCount = await this.orm.searchCount(
                "hr.attendance",
                [],

            );
            this.state.attendanceCount = recordCount;
        } catch (e) {
            console.error("No se pudo refrescar el dashboard", e);
        } finally {
            this.state.loading = false;
        }
    }
}