import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";


export class AttendanceDashboard extends Component {
    static template = "hr_attendance_dashboard.AttendanceDashboard";

    setup() {
        this.orm = useService("orm");

        this.state = useState({
            userName: "",
            attendanceCount: 0,
            loading: true,
        });

        onWillStart(async () => {
            this.state.userName = session.userName;
            
            const recordCount = await this.orm.searchCount(
                "hr.attendance",
                [],

            );
            
            this.state.attendanceCount = recordCount;
            this.state.loading = false;
        });
    }

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