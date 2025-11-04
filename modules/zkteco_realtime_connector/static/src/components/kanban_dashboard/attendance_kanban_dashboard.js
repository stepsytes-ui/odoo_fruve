/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

export class AttendanceKanbanDashboard extends Component {
    // Apunta a la plantilla XML que crearemos en el siguiente paso
    static template = "zkteco_realtime_connector.AttendanceKanbanDashboard";

    setup() {
        this.orm = useService("orm");

        const today = new Date().toISOString().split("T")[0]; // formato YYYY-MM-DD

        this.state = useState({
            loading: true,
            start_date: today,  // fecha inicial por defecto = hoy
            end_date: today,    // fecha final por defecto = hoy
            stats: {
                present_count: 0,
                excused_count: 0,
                unexcused_count: 0,
            },
        });

        onWillStart(async () => {
            await this.loadStats();
        });
    }

    async loadStats() {
        this.state.loading = true;
        try {
            const stats = await this.orm.call(
                "hr.attendance",
                "get_attendance_dashboard_stats",
                [],
                {
                    start_date: this.state.start_date,
                    end_date: this.state.end_date,
                }
            );
            this.state.stats = stats;
        } catch (e) {
            console.error("Error al cargar estadísticas:", e);
        } finally {
            this.state.loading = false;
        }
    }

    async _onRefreshClick() {
        await this.loadStats();
    }

}

registry.category("components").add("attendance_kanban_dashboard", AttendanceKanbanDashboard);