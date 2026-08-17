/** @odoo-module */

import {Component, onWillStart, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class OvertimeDashboard extends Component {
    static props = {
        onChangeDates: {type: Function, optional: true},
        onFilterEmployee: {type: Function, optional: true},
    }

    static template = "overtime.OvertimeDashboard";

    setup(){
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        const today = new Date();
        const localToday = new Date(today.getTime() - today.getTimezoneOffset() * 60000)
            .toISOString()
            .split("T")[0];
        this.state = useState({
            loading: true,
            start_date: localToday,
            end_date: localToday,

            stats:{
                total_employees: 0,
                total_hours: 0,
                total_play: 0,
            },
            tableHeaders: [],
            tableRows: [],
            columnTotals: {},
            grandTotalHours: 0,
            grandTotalAmount: 0,
        });

        // Restaurar fechas desde localStorage si existen
        try{
            const saved = window.localStorage.getItem('overtime_dashboard_dates');
            if (saved) {
                const parsed = JSON.parse(saved);
                if (parsed.start_date) this.state.start_date = parsed.start_date;
                if (parsed.end_date) this.state.end_date = parsed.end_date;
            }
        } catch (e) {
            // ignore
        }

        onWillStart(async () => {
            await this.loadStats();
        });
    }

    async _onRefresh() {
        await this.loadStats();
        if (this.props.onChangeDates) {
            this.props.onChangeDates(this.state.start_date, this.state.end_date);
        }
        // Persistir fechas para mantenerlas al navegar fuera/volver
        try{
            window.localStorage.setItem('overtime_dashboard_dates', JSON.stringify({
                start_date: this.state.start_date,
                end_date: this.state.end_date,
            }));
        } catch (e) {
            // ignore
        }
    }

    async loadStats(){
        this.state.loading = true;
        try{
            const stats = await this.orm.call(
                "overtime",
                "get_overtime_dashboard_stats",
                [],
                {
                    start_date: this.state.start_date,
                    end_date: this.state.end_date,
                }
            );
            this.state.stats = stats;

            // Cargar datos de la tabla con estructura de días dinámicos
            const tableData = await this.orm.call(
                "overtime",
                "get_overtime_table_data",
                [],
                {
                    start_date: this.state.start_date,
                    end_date: this.state.end_date,
                }
            );
            this.state.tableHeaders = tableData.headers || [];
            this.state.tableRows = tableData.rows || [];
            this.state.columnTotals = tableData.column_totals || {};
            this.state.grandTotalHours = tableData.grand_total_hours || 0;
            this.state.grandTotalAmount = tableData.grand_total_amount || 0;
        } catch (e){
            console.error("Error al cargar estadisticas de tiempo extra:", e);
        } finally {
            this.state.loading = false;
        }
    }

    onClickRow(employeeNumber, employeeName) {
        if (this.props.onFilterEmployee) {
            this.props.onFilterEmployee(employeeNumber, employeeName);
        }
    }

    onPrintDashboard() {
        window.print();
    }

    async onExportExcel() {
        try {
            const result = await this.orm.call(
                "overtime",
                "export_overtime_table_excel",
                [],
                {
                    start_date: this.state.start_date,
                    end_date: this.state.end_date,
                }
            );
            if (!result || !result.file_content) {
                return;
            }
            const mimeType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
            const binary = window.atob(result.file_content);
            const byteArray = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                byteArray[i] = binary.charCodeAt(i);
            }
            const blob = new Blob([byteArray], { type: mimeType });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = result.file_name || "tiempo_extra.xlsx";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (e) {
            console.error("Error al exportar Excel de tiempo extra:", e);
            this.notification.add("No fue posible exportar el archivo de Excel.", {
                type: "danger",
            });
        }
    }

}
