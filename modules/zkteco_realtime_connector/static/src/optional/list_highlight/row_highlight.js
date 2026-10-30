/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onWillUnmount, useEffect, useState } from "@odoo/owl";

const COLORS = [
    ["yellow", "Amarillo", "#fff59d"],
    ["blue", "Azul", "#90caf9"],
    ["green", "Verde", "#a5d6a7"],
    ["orange", "Naranja", "#ffcc80"],
    ["red", "Rojo", "#ef9a9a"],
    ["pink", "Rosa", "#f8bbd0"],
];

function storageKey(resModel) {
    return `fruve_row_highlights:${resModel}`;
}

function loadHighlights(resModel) {
    try {
        return JSON.parse(window.localStorage.getItem(storageKey(resModel))) || {};
    } catch {
        return {};
    }
}

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.fruveHl = useState({ map: loadHighlights(this.props.list.resModel) });
        this._fruveMenu = null;

        const closeMenu = () => {
            if (this._fruveMenu) {
                this._fruveMenu.remove();
                this._fruveMenu = null;
            }
        };
        const onContextMenu = (ev) => {
            const root = this.rootRef && this.rootRef.el;
            if (root && root.contains(ev.target)) {
                this._fruveOnContextMenu(ev, closeMenu);
            }
        };
        const onDocClick = (ev) => {
            if (this._fruveMenu && !this._fruveMenu.contains(ev.target)) {
                closeMenu();
            }
        };
        const onKey = (ev) => ev.key === "Escape" && closeMenu();

        useEffect(
            () => {
                document.addEventListener("contextmenu", onContextMenu, true);
                document.addEventListener("mousedown", onDocClick, true);
                document.addEventListener("keydown", onKey, true);
                window.addEventListener("scroll", closeMenu, true);
                return () => {
                    document.removeEventListener("contextmenu", onContextMenu, true);
                    document.removeEventListener("mousedown", onDocClick, true);
                    document.removeEventListener("keydown", onKey, true);
                    window.removeEventListener("scroll", closeMenu, true);
                };
            },
            () => []
        );
        onWillUnmount(closeMenu);
    },

    getRowClass(record) {
        let classes = super.getRowClass(...arguments);
        const color = this.fruveHl && record.resId && this.fruveHl.map[record.resId];
        if (color) {
            classes += ` fruve_hl_${color}`;
        }
        return classes;
    },

    _fruveSetColor(record, color) {
        const resModel = this.props.list.resModel;
        const map = { ...loadHighlights(resModel) };
        if (color) {
            map[record.resId] = color;
        } else {
            delete map[record.resId];
        }
        try {
            window.localStorage.setItem(storageKey(resModel), JSON.stringify(map));
        } catch {
            // almacenamiento no disponible: solo se mantiene en memoria
        }
        this.fruveHl.map = map;
    },

    _fruveOnContextMenu(ev, closeMenu) {
        const cell = ev.target.closest("td.o_data_cell");
        const row = cell && cell.closest("tr.o_data_row");
        if (!row) {
            return;
        }
        const record = this.props.list.records.find((r) => r.id === row.dataset.id);
        if (!record || !record.resId) {
            return;
        }
        ev.preventDefault();
        closeMenu();

        const menu = document.createElement("div");
        menu.className = "fruve_hl_menu";
        const title = document.createElement("div");
        title.className = "fruve_hl_title";
        title.textContent = "Subrayar fila";
        menu.appendChild(title);

        const addItem = (label, dotColor, color) => {
            const item = document.createElement("div");
            item.className = "fruve_hl_item";
            const dot = document.createElement("span");
            dot.className = "fruve_hl_dot";
            dot.style.background = dotColor || "transparent";
            item.append(dot, document.createTextNode(label));
            item.addEventListener("click", () => {
                this._fruveSetColor(record, color);
                closeMenu();
            });
            menu.appendChild(item);
        };
        for (const [key, label, hex] of COLORS) {
            addItem(label, hex, key);
        }
        if (this.fruveHl.map[record.resId]) {
            addItem("Quitar subrayado", null, null);
        }

        document.body.appendChild(menu);
        const { innerWidth, innerHeight } = window;
        const rect = menu.getBoundingClientRect();
        menu.style.left = `${Math.min(ev.clientX, innerWidth - rect.width - 4)}px`;
        menu.style.top = `${Math.min(ev.clientY, innerHeight - rect.height - 4)}px`;
        this._fruveMenu = menu;
    },
});
