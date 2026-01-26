/** @odoo-module */

import {Component, onWillStart, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";
import {session} from "@web/session";

export class OvertimeDashboard extends Component {
    static props = {
        onChangeDates: {type: Function, optional: true},
        onFilterEmployee: {type: Function, optional: true},
    }

    static template = "overtime.OvertimeDashboard";

    setup(){
        this.orm = useService("orm");
        
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

}
