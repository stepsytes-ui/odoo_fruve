/** @odoo-module */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const DAY_LABELS = ["Vie", "Sab", "Dom", "Lun", "Mar", "Mie", "Jue"];

function toDateObject(startDateValue) {
    if (!startDateValue) {
        return null;
    }
    if (startDateValue instanceof Date) {
        return Number.isNaN(startDateValue.getTime()) ? null : startDateValue;
    }
    if (typeof startDateValue === "string") {
        const parsed = new Date(`${startDateValue}T00:00:00`);
        return Number.isNaN(parsed.getTime()) ? null : parsed;
    }
    if (startDateValue.toISODate instanceof Function) {
        const parsed = new Date(`${startDateValue.toISODate()}T00:00:00`);
        return Number.isNaN(parsed.getTime()) ? null : parsed;
    }
    return null;
}

function parseDailyMinutes(value) {
    if (!value) {
        return [0, 0, 0, 0, 0, 0, 0];
    }
    try {
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed) && parsed.length === 7) {
            return parsed.map((v) => {
                const n = parseInt(v, 10);
                return Number.isFinite(n) && n >= 0 ? n : 0;
            });
        }
    } catch (e) {
        // Ignore malformed values and fallback to zeros.
    }
    return [0, 0, 0, 0, 0, 0, 0];
}

function formatDayHeader(startDateString, index) {
    const baseDate = toDateObject(startDateString);
    if (!baseDate) {
        return `${DAY_LABELS[index]} --`;
    }
    const base = new Date(baseDate.getTime());
    base.setDate(base.getDate() + index);
    const day = String(base.getDate()).padStart(2, "0");
    return `${DAY_LABELS[index]} ${day}`;
}

export class LateWeeklyBreakdownField extends Component {
    static template = "zkteco_realtime_connector.LateWeeklyBreakdownField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
    }

    get isReadonly() {
        return !!this.props.readonly;
    }

    get dailyMinutes() {
        return parseDailyMinutes(this.props.record.data[this.props.name]);
    }

    get headers() {
        const startDate = this.props.record.data.week_start_date;
        return DAY_LABELS.map((_, index) => formatDayHeader(startDate, index));
    }

    get totalMinutes() {
        return this.dailyMinutes.reduce((acc, v) => acc + v, 0);
    }

    get baseDailyMinutes() {
        return parseDailyMinutes(this.props.record.data.base_daily_minutes_json);
    }

    get payableDays() {
        const decimalHours = this.totalMinutes / 60;
        const days = 6 - decimalHours / 8;
        return Math.max(0, Math.round(days * 100) / 100);
    }

    async onInputMinutes(index, ev) {
        const parsed = parseInt(ev.target.value || "0", 10);
        const value = Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
        const next = [...this.dailyMinutes];
        next[index] = value;
        const total = next.reduce((acc, v) => acc + v, 0);
        const decimalHours = total / 60;
        const days = Math.max(0, Math.round((6 - decimalHours / 8) * 100) / 100);

        await this.props.record.update({
            [this.props.name]: JSON.stringify(next),
            total_late_minutes: total,
            payable_days: days,
        });
    }

    async onResetClick() {
        const model = this.props.record.resModel;
        const recordId = this.props.record.resId;
        if (!model || !recordId) {
            return;
        }

        await this.orm.call(model, "action_reset_weekly_adjustment", [[recordId]]);

        const baseDaily = this.baseDailyMinutes;
        const baseTotal = baseDaily.reduce((acc, v) => acc + v, 0);
        const basePayable = this.props.record.data.base_payable_days;

        await this.props.record.update({
            [this.props.name]: JSON.stringify(baseDaily),
            total_late_minutes: baseTotal,
            payable_days: basePayable,
            has_manual_override: false,
        });
    }
}

export const lateWeeklyBreakdownField = {
    component: LateWeeklyBreakdownField,
    supportedTypes: ["text"],
};

registry.category("fields").add("late_weekly_breakdown", lateWeeklyBreakdownField);
