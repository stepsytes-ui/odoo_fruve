/** @odoo-module */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { AttendanceKanbanDashboard } from "../components/kanban_dashboard/attendance_kanban_dashboard";

const attendanceListView = registry.category("views").get("attendance_list_view");

export class AttendanceDashboardWrapper extends Component {
    static template = "zkteco_realtime_connector.AttendanceDashboardWrapper";
    static components = { 
        AttendanceKanbanDashboard,
        DynamicView: attendanceListView.Controller,
    };

    get dynamicViewProps() {
        return { ...this.props,
            
         };
    }
}
