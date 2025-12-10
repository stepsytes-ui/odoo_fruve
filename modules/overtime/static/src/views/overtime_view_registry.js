/** @odoo-module */

import { registry } from "@web/core/registry";
import { OvertimeDashboardWrapper, setOriginalListController } from "./overtime_dashboard_wrapper";

const listView = registry.category("views").get("list");

const originalListController = listView.Controller;
setOriginalListController(originalListController);

registry.category("views").add("list", {
    ...listView,
    Controller: OvertimeDashboardWrapper,
}, { force: true });

