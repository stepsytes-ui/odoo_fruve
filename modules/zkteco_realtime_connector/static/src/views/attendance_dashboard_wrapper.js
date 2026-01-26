/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { AttendanceKanbanDashboard } from "../components/kanban_dashboard/attendance_kanban_dashboard";

const attendanceListView = registry.category("views").get("attendance_list_view");

export class AttendanceDashboardWrapper extends Component {
    static template = "zkteco_realtime_connector.AttendanceDashboardWrapper";
    static components = { 
        AttendanceKanbanDashboard,
        DynamicView: attendanceListView.Controller,
    };

    setup() {
        this.state = useState({
            startDate: new Date().toISOString().split("T")[0],
            endDate: new Date().toISOString().split("T")[0],
        });

        // Restaurar fechas persistidas (si el usuario navegó fuera/volvió)
        try {
            const saved = window.localStorage.getItem('attendance_dashboard_dates');
            if (saved) {
                const parsed = JSON.parse(saved);
                if (parsed.start_date) this.state.startDate = parsed.start_date;
                if (parsed.end_date) this.state.endDate = parsed.end_date;
            }
        } catch (e) {
            // ignore
        }

        this.onDashboardFilter = this.onDashboardFilter.bind(this);
    }

    onDashboardFilter(startDate, endDate) {
        this.state.startDate = startDate;
        this.state.endDate = endDate;
        // Persistir fechas para mantener estado entre navegaciones
        try {
            window.localStorage.setItem('attendance_dashboard_dates', JSON.stringify({
                start_date: this.state.startDate,
                end_date: this.state.endDate,
            }));
        } catch (e) {
            // ignore
        }
    }

    get dynamicViewProps() {
        const baseProps = {
            ...this.props,
        };

        // Resolver el dominio base desde props o action
        let baseDomain = baseProps.domain ?? (baseProps.action && baseProps.action.domain) ?? [];
        if (!Array.isArray(baseDomain)) {
            baseDomain = [];
        }

        // Añadir filtro de fechas si hay fechas seleccionadas
        if (this.state.startDate && this.state.endDate) {
            // Convertir fechas locales a UTC para coincidir con cómo están almacenadas en Odoo
            const startDate = new Date(this.state.startDate + 'T00:00:00');
            const endDate = new Date(this.state.endDate + 'T23:59:59');
            
            // Convertir a formato ISO UTC (Odoo espera formato 'YYYY-MM-DD HH:MM:SS')
            const startDateTime = startDate.toISOString().replace('T', ' ').substring(0, 19);
            const endDateTime = endDate.toISOString().replace('T', ' ').substring(0, 19);
            
            baseDomain = [...baseDomain, ['check_in', '>=', startDateTime], ['check_in', '<=', endDateTime]];
        }

        return {
            ...baseProps,
            domain: baseDomain,
        };
    }
}
