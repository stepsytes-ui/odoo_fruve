/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { OvertimeDashboard } from "../components/overtime_dashboard/overtime_dashboard";
import { registry } from "@web/core/registry";

// El controlador original será pasado dinámicamente
let originalListController = null;

export class OvertimeDashboardWrapper extends Component{
    static template = "overtime.OvertimeDashboardWrapper";
    
    static components = {};

    setup() {
        // Inicializar componentes dinámicamente
        if (!originalListController) {
            // En caso de que no esté disponible, obtenerlo del registry importado
            try {
                const listView = registry.category("views").get("list");
                originalListController = listView.Controller;
                console.log("⚠️ originalListController obtenido dinámicamente");
            } catch (e) {
                console.warn("No se pudo obtener originalListController desde registry aún:", e);
            }
        }
        
        OvertimeDashboardWrapper.components = {
            OvertimeDashboard,
            DynamicView: originalListController,
        };

        this.state = useState({
            startDate: new Date().toISOString().split("T")[0],
            endDate: new Date().toISOString().split("T")[0],
            selectedEmployeeNumber: null,
        });

        // Restaurar fechas persistidas (si el usuario navegó fuera/volvió)
        try {
            const saved = window.localStorage.getItem('overtime_dashboard_dates');
            if (saved) {
                const parsed = JSON.parse(saved);
                if (parsed.start_date) this.state.startDate = parsed.start_date;
                if (parsed.end_date) this.state.endDate = parsed.end_date;
            }
        } catch (e) {
            // ignore
        }

        this.onDatesUpdated = this.onDatesUpdated.bind(this);
        this.onFilterEmployee = this.onFilterEmployee.bind(this);
    }

    onFilterEmployee(employeeNumber, employeeName) {
        this.state.selectedEmployeeNumber = employeeNumber;
        console.log(`Filtrando por empleado: ${employeeName} (${employeeNumber})`);
    }

    onDatesUpdated(startDate, endDate) {
        this.state.startDate = startDate;
        this.state.endDate = endDate;
        // Persistir fechas para mantener estado entre navegaciones
        try{
            window.localStorage.setItem('overtime_dashboard_dates', JSON.stringify({
                start_date: startDate,
                end_date: endDate,
            }));
        } catch (e) {}

        try {
            if (this.shouldRenderDashboard) {
                const baseContext = (this.props && this.props.context) || (this.props && this.props.action && this.props.action.context) || {};
                const newContext = {
                    ...baseContext,
                    list_start_date: startDate,
                    list_end_date: endDate,
                    search_default_dashboard_date: 1,
                };
                if (this.props && this.props.model && typeof this.props.model.load === 'function') {
                    this.props.model.load({ context: newContext });
                }
            }
        } catch (e) {
        
        }
    }

    get dynamicViewProps() {
        const baseProps = {
            ...this.props,
        };

        // Resolver el dominio base desde props o action
        let baseDomain = baseProps.domain ?? (baseProps.action && baseProps.action.domain) ?? [];
        if (!Array.isArray(baseDomain)) {
            baseDomain = [baseDomain];
        } else {
            // copiar para no mutar
            baseDomain = baseDomain.slice();
        }

        // Solo añadir filtro de fechas si estamos en la vista de dashboard (approved)
        if (this.shouldRenderDashboard && this.state.startDate && this.state.endDate) {
            baseDomain = baseDomain.concat([
                ['requested_date', '>=', this.state.startDate],
                ['requested_date', '<=', this.state.endDate],
            ]);
        }

        // Añadir filtro de empleado si está seleccionado
        if (this.state.selectedEmployeeNumber) {
            baseDomain = baseDomain.concat([
                ['biometric_id', '=', this.state.selectedEmployeeNumber],
            ]);
        }

        const newContext = {
            ...(baseProps.context || {}),
            list_start_date: this.state.startDate,
            list_end_date: this.state.endDate,
        };

        return {
            ...baseProps,
            domain: baseDomain,
            context: newContext,
        };
    }

    get shouldRenderDashboard() {
        const resolvedModel = this.props.model ?? this.props.resModel ?? this.props.res_model ?? (this.props.view && this.props.view.model) ?? null;
            // Buscar domain en varias fuentes
            const domain = this.props.domain ?? (this.props.action && this.props.action.domain) ?? (this.props.view && this.props.view.arch && this.props.view.arch.attrs && this.props.view.arch.attrs.domain) ?? null;
            const context = this.props.context ?? (this.props.action && this.props.action.context) ?? null;

            const domainHasApproved = (dom) => {
                if (!dom) return false;
                try {
                    // dom can be array with tuples and operators like '|'
                    const stack = Array.isArray(dom) ? dom.slice() : [dom];
                    for (const item of stack) {
                        if (Array.isArray(item) && item.length >= 3) {
                            const [field, op, value] = item;
                            if (field === 'state' && (op === '=' || op === 'in')) {
                                if (op === '=' && value === 'approved') return true;
                                if (op === 'in' && Array.isArray(value) && value.indexOf('approved') !== -1) return true;
                            }
                        }
                        // if nested lists exist, push their children
                        if (Array.isArray(item)) {
                            for (const sub of item) {
                                if (Array.isArray(sub)) stack.push(sub);
                            }
                        }
                    }
                } catch (e) {
                    console.warn('Error parsing domain for approved check', e);
                }
                return false;
            };

            const contextHasApproved = (ctx) => {
                if (!ctx) return false;
                try {
                    if (ctx.default_state === 'approved' || ctx.state === 'approved') return true;
                } catch (e) {}
                return false;
            };

            const isApproved = domainHasApproved(domain) || contextHasApproved(context);
            return resolvedModel === 'overtime' && isApproved;
    }
}

// Exporta una función para asignar el controlador original desde el registry
export function setOriginalListController(controller) {
    originalListController = controller;
    OvertimeDashboardWrapper.components = {
        OvertimeDashboard,
        DynamicView: originalListController,
    };
}
