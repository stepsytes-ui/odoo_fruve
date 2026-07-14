/** @odoo-module */

import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

const PURCHASE_ALERT_STORAGE_KEY = "Warehouse_Management.purchase_alerts_opened";

registry.category("services").add("compras_purchase_alert_service", {
    dependencies: ["action", "orm", "notification"],
    start(env, { action, orm, notification }) {
        const openAlerts = async () => {
            try {
                if (window.sessionStorage.getItem(PURCHASE_ALERT_STORAGE_KEY) === "1") {
                    return;
                }

                const isEncargado = await user.hasGroup("Warehouse_Management.group_compras_encargado");
                const isAlmacenista = await user.hasGroup("Warehouse_Management.group_compras_almacenista");
                if (!isEncargado && !isAlmacenista) {
                    return;
                }

                const alertAction = await orm.call(
                    "compras.product.alert.wizard",
                    "action_open_current_user_wizard",
                    [],
                    {}
                );
                if (!alertAction) {
                    return;
                }

                await action.doAction(alertAction);
                window.sessionStorage.setItem(PURCHASE_ALERT_STORAGE_KEY, "1");
            } catch (error) {
                notification.add(
                    "No se pudieron cargar las alertas de compras.",
                    {
                        title: "Compras Fruvemex",
                        type: "warning",
                    }
                );
            }
        };

        queueMicrotask(openAlerts);

        return {};
    },
});