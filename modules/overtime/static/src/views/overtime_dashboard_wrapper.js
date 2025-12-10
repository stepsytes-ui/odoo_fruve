/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { OvertimeDashboard } from "../components/overtime_dashboard/overtime_dashboard";

// No importar del registry aquí para evitar dependencia circular
// El controlador original será pasado dinámicamente

let originalListController = null;

export class OvertimeDashboardWrapper extends Component{
    static template = "overtime.OvertimeDashboardWrapper";
    
    static components = {};

    setup() {
        console.log("🔔 OvertimeDashboardWrapper.setup() - props:", this.props);
        console.log("🔔 Model:", this.props.model);
        
        // Inicializar componentes dinámicamente
        if (!originalListController) {
            // En caso de que no esté disponible, obtenerlo del registry aquí
            const { registry } = owl.core;
            const listView = registry.category("views").get("list");
            originalListController = listView.Controller;
            console.log("⚠️ originalListController obtenido dinámicamente");
        }
        
        OvertimeDashboardWrapper.components = {
            OvertimeDashboard,
            DynamicView: originalListController,
        };

        this.state = useState({
            startDate: new Date().toISOString().split("T")[0],
            endDate: new Date().toISOString().split("T")[0],
        });

        this.onDatesUpdated = this.onDatesUpdated.bind(this);
    }

    onDatesUpdated(startDate, endDate) {
        this.state.startDate = startDate;
        this.state.endDate = endDate;
    }

    get dynamicViewProps() {
        return { 
            ...this.props,
        };
    }

    get shouldRenderDashboard() {
        const resolvedModel = this.props.model ?? this.props.resModel ?? this.props.res_model ?? (this.props.view && this.props.view.model) ?? null;
        console.log("🔔 shouldRenderDashboard - resolvedModel:", resolvedModel, "propsKeys:", Object.keys(this.props));
            // Buscar domain en varias fuentes
            const domain = this.props.domain ?? (this.props.action && this.props.action.domain) ?? (this.props.view && this.props.view.arch && this.props.view.arch.attrs && this.props.view.arch.attrs.domain) ?? null;
            const context = this.props.context ?? (this.props.action && this.props.action.context) ?? null;

            console.log("🔔 shouldRenderDashboard - resolvedModel:", resolvedModel, "domain:", domain, "context:", context);

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
            console.log('🔔 shouldRenderDashboard - isApproved:', isApproved);

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
    console.log("✅ setOriginalListController llamado");
}
