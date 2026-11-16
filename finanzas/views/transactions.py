"""Listado de movimientos con filtros, edición y exportación."""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
import tkinter as tk
from tkinter import filedialog, ttk

from .. import theme
from ..dialogs import TransactionDialog, ask_confirm
from ..theme import font
from ..utils import fmt_date, parse_date, truncate
from ..widgets import Card, form_label
from . import BaseView

KIND_LABELS = {"ingreso": "Ingreso", "egreso": "Egreso", "transferencia": "Transferencia"}
KIND_FILTERS = {
    "Todos": None, "Ingresos": "ingreso", "Egresos": "egreso",
    "Transferencias": "transferencia",
}

PAGE_SIZE = 50
FILTERS_KEY = "tx_filters"

# columna visible -> clave de orden en la base de datos
SORT_KEYS = {
    "fecha": "fecha",
    "tipo": "tipo",
    "desc": "descripcion",
    "cat": "categoria",
    "cuenta": "cuenta",
    "monto": "monto",
}
COLUMNS = (
    ("fecha", "Fecha", 92, "w", False),
    ("tipo", "Tipo", 105, "w", False),
    ("desc", "Descripción", 270, "w", True),
    ("cat", "Categoría", 145, "w", False),
    ("cuenta", "Cuenta", 190, "w", False),
    ("monto", "Monto", 170, "e", False),
)
DEFAULT_DESC = {"fecha": True, "monto": True}


class TransactionsView(BaseView):
    title = "Movimientos"
    subtitle = "Registra y revisa cada ingreso, egreso y transferencia"

    def __init__(self, app):
        super().__init__(app)
        self._search_job = None
        self.cat_map: dict[str, int | None] = {}
        self.acc_map: dict[str, int | None] = {}
        self.page = 0
        self.sort_column = "fecha"
        self.sort_desc = True
        self._date_from: str | None = None
        self._date_to: str | None = None
        self._pending_filters = (-1, -1)  # -1 = no guardado
        self._restored_filters = False
        self._build()
        self._apply_saved_filters()

    # ------------------------------------------------------------ interfaz
    def _build(self):
        filters_card = Card(self, padding=14)
        filters_card.pack(fill="x")

        grid = tk.Frame(filters_card.inner, bg=theme.CARD)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=3, uniform="f")
        for col in range(1, 6):
            grid.columnconfigure(col, weight=2, uniform="f")

        self.search_var = tk.StringVar()
        self.kind_var = tk.StringVar(value="Todos")
        self.cat_var = tk.StringVar(value="Todas")
        self.acc_var = tk.StringVar(value="Todas")
        self.date_from_var = tk.StringVar()
        self.date_to_var = tk.StringVar()

        search_holder = tk.Frame(grid, bg=theme.CARD)
        search_holder.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        form_label(search_holder, "BUSCAR").pack(fill="x", pady=(0, 4))
        entry = ttk.Entry(search_holder, textvariable=self.search_var)
        entry.pack(fill="x")
        entry.bind("<KeyRelease>", self._on_search)
        self.search_entry = entry

        self._combo(grid, 1, "TIPO", self.kind_var,
                    ["Todos", "Ingresos", "Egresos", "Transferencias"], padx=(0, 10))
        self.combo_category = self._combo(grid, 2, "CATEGORÍA", self.cat_var,
                                          ["Todas"], padx=(0, 10))
        self.combo_account = self._combo(grid, 3, "CUENTA", self.acc_var,
                                         ["Todas"], padx=(0, 10))
        self._date_field(grid, 4, "DESDE", self.date_from_var, padx=(0, 10))
        self._date_field(grid, 5, "HASTA", self.date_to_var, padx=(0, 10))

        ttk.Button(grid, text="Limpiar", style="Ghost.TButton",
                   command=self._clear_filters).grid(row=0, column=6, sticky="s", pady=(0, 1))

        self.range_hint = tk.Label(
            filters_card.inner, text="", bg=theme.CARD, fg=theme.SUBTLE,
            font=font(8), anchor="w",
        )
        self.range_hint.pack(fill="x", pady=(6, 0))

        table_card = Card(self, padding=16)
        table_card.pack(fill="both", expand=True, pady=(14, 0))

        head = tk.Frame(table_card.inner, bg=theme.CARD)
        head.pack(fill="x")
        summary = tk.Frame(head, bg=theme.CARD)
        summary.pack(side="left", anchor="w")
        self.lbl_count = tk.Label(summary, text="0 movimientos", bg=theme.CARD,
                                  fg=theme.MUTED, font=font(9))
        self.lbl_income = tk.Label(summary, text="", bg=theme.CARD, fg=theme.GREEN,
                                   font=font(9, "bold"))
        self.lbl_expense = tk.Label(summary, text="", bg=theme.CARD, fg=theme.RED,
                                    font=font(9, "bold"))
        self.lbl_net = tk.Label(summary, text="", bg=theme.CARD, fg=theme.TEXT,
                                font=font(9, "bold"))
        self.lbl_count.pack(side="left")
        for widget in (self.lbl_income, self.lbl_expense, self.lbl_net):
            tk.Label(summary, text="·", bg=theme.CARD, fg=theme.SUBTLE,
                     font=font(9)).pack(side="left", padx=7)
            widget.pack(side="left")

        ttk.Button(head, text="Exportar CSV", style="Ghost.TButton",
                   command=self._export).pack(side="right")
        self.btn_delete = ttk.Button(head, text="Eliminar", style="Danger.TButton",
                                     command=self._delete, state="disabled")
        self.btn_delete.pack(side="right", padx=6)
        self.btn_edit = ttk.Button(head, text="Editar", style="Secondary.TButton",
                                   command=self._edit, state="disabled")
        self.btn_edit.pack(side="right", padx=6)

        holder = tk.Frame(table_card.inner, bg=theme.CARD)
        holder.pack(fill="both", expand=True, pady=(10, 0))
        self.tree = ttk.Treeview(holder, columns=[c[0] for c in COLUMNS],
                                 show="headings", selectmode="browse")
        for col, label, width, anchor, stretch in COLUMNS:
            self.tree.heading(col, text=label, anchor=anchor,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=width, anchor=anchor, stretch=stretch, minwidth=60)

        vsb = ttk.Scrollbar(holder, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.empty_lbl = tk.Label(
            holder, text="", bg=theme.CARD, fg=theme.SUBTLE, font=font(10),
            justify="center", wraplength=420,
        )

        self.tree.tag_configure("ingreso", background=theme.GREEN_SOFT,
                                foreground=theme.GREEN_DARK)
        self.tree.tag_configure("egreso", background=theme.RED_SOFT,
                                foreground=theme.RED_DARK)
        self.tree.tag_configure("transferencia", background=theme.BLUE_SOFT,
                                foreground=theme.BLUE_DARK)

        self.tree.bind("<Double-1>", lambda _e: self._edit())
        self.tree.bind("<Delete>", lambda _e: self._delete())
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Button-3>", self._show_menu)

        self.menu = tk.Menu(self, tearoff=0, font=font(9))
        self.menu.add_command(label="Editar movimiento", command=self._edit)
        self.menu.add_separator()
        self.menu.add_command(label="Eliminar movimiento", command=self._delete)

        footer = tk.Frame(table_card.inner, bg=theme.CARD)
        footer.pack(fill="x", pady=(8, 0))

        self.range_lbl = tk.Label(footer, text="", bg=theme.CARD, fg=theme.SUBTLE,
                                  font=font(8), anchor="w")
        self.range_lbl.pack(side="left")

        self.btn_next = ttk.Button(footer, text="Siguiente →", style="Ghost.TButton",
                                   command=lambda: self._change_page(1))
        self.btn_next.pack(side="right")
        self.page_lbl = tk.Label(footer, text="", bg=theme.CARD, fg=theme.MUTED,
                                 font=font(8))
        self.page_lbl.pack(side="right", padx=10)
        self.btn_prev = ttk.Button(footer, text="← Anterior", style="Ghost.TButton",
                                   command=lambda: self._change_page(-1))
        self.btn_prev.pack(side="right")

        self.note_lbl = tk.Label(table_card.inner, text="", bg=theme.CARD,
                                 fg=theme.SUBTLE, font=font(8), anchor="w")
        self.note_lbl.pack(fill="x", pady=(4, 0))

    def _combo(self, parent, col, label, var, values, padx=(0, 0)):
        holder = tk.Frame(parent, bg=theme.CARD)
        holder.grid(row=0, column=col, sticky="ew", padx=padx)
        form_label(holder, label).pack(fill="x", pady=(0, 4))
        combo = ttk.Combobox(holder, textvariable=var, values=values, state="readonly")
        combo.pack(fill="x")
        combo.bind("<<ComboboxSelected>>", lambda _e: self._on_filter_change())
        return combo

    def _date_field(self, parent, col, label, var, padx=(0, 0)):
        holder = tk.Frame(parent, bg=theme.CARD)
        holder.grid(row=0, column=col, sticky="ew", padx=padx)
        form_label(holder, label).pack(fill="x", pady=(0, 4))
        entry = ttk.Entry(holder, textvariable=var, width=12)
        entry.pack(fill="x")
        entry.bind("<KeyRelease>", self._on_search)
        entry.bind("<FocusOut>", lambda _e: self._on_filter_change())

    # ------------------------------------------------------------ filtros
    def _apply_saved_filters(self):
        try:
            raw = self.db.get_setting(FILTERS_KEY, "")
            saved = json.loads(raw) if raw else {}
        except (ValueError, TypeError, sqlite3.Error):
            saved = {}
        if not isinstance(saved, dict):
            saved = {}
        self.search_var.set(str(saved.get("text", "")))
        kind = saved.get("kind")
        for label, value in KIND_FILTERS.items():
            if value == kind:
                self.kind_var.set(label)
                break
        self.date_from_var.set(str(saved.get("date_from", "")))
        self.date_to_var.set(str(saved.get("date_to", "")))
        sort_column = saved.get("sort")
        if sort_column in SORT_KEYS:
            self.sort_column = sort_column
        self.sort_desc = bool(saved.get("desc", True))
        self._pending_filters = (
            saved.get("category_id", -1),
            saved.get("account_id", -1),
        )

    def _restore_filter_selections(self):
        cat_id, acc_id = self._pending_filters
        if cat_id != -1:
            if cat_id == 0:
                self.cat_var.set("Sin categoría")
            elif cat_id is None:
                self.cat_var.set("Todas")
            else:
                display = next((k for k, v in self.cat_map.items() if v == cat_id), "Todas")
                self.cat_var.set(display)
        if acc_id != -1:
            if acc_id is None:
                self.acc_var.set("Todas")
            else:
                display = next((k for k, v in self.acc_map.items() if v == acc_id), "Todas")
                self.acc_var.set(display)
        self._restored_filters = True

    def _save_filters(self):
        data = {
            "text": self.search_var.get().strip(),
            "kind": KIND_FILTERS.get(self.kind_var.get()),
            "category_id": self.cat_map.get(self.cat_var.get()),
            "account_id": self.acc_map.get(self.acc_var.get()),
            "date_from": self.date_from_var.get().strip(),
            "date_to": self.date_to_var.get().strip(),
            "sort": self.sort_column,
            "desc": self.sort_desc,
        }
        try:
            self.db.set_setting(FILTERS_KEY, json.dumps(data, ensure_ascii=False))
        except sqlite3.Error:
            pass

    def _refresh_category_filter(self):
        cats = self.db.categories(include_archived=False)
        names = [c["name"] for c in cats]
        values = ["Todas", "Sin categoría"]
        self.cat_map = {"Todas": None, "Sin categoría": 0}
        for cat in cats:
            display = cat["name"]
            if names.count(cat["name"]) > 1:
                display += " (ingreso)" if cat["kind"] == "ingreso" else " (gasto)"
            self.cat_map[display] = cat["id"]
            values.append(display)
        if self.cat_var.get() not in values:
            self.cat_var.set("Todas")
        self.combo_category.configure(values=values)

        accounts = self.db.accounts()
        acc_values = ["Todas"] + [a["name"] for a in accounts]
        self.acc_map = {"Todas": None}
        self.acc_map.update({a["name"]: a["id"] for a in accounts})
        if self.acc_var.get() not in acc_values:
            self.acc_var.set("Todas")
        self.combo_account.configure(values=acc_values)

    def _clear_filters(self):
        self.search_var.set("")
        self.kind_var.set("Todos")
        self.cat_var.set("Todas")
        self.acc_var.set("Todas")
        self.date_from_var.set("")
        self.date_to_var.set("")
        self.page = 0
        self.refresh()

    def _on_search(self, _event=None):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(300, self._on_filter_change)

    def _on_filter_change(self):
        self._search_job = None
        self.page = 0
        self.refresh()

    def _parse_dates(self):
        """Devuelve (desde, hasta) en ISO y muestra un aviso si el rango no es válido."""
        raw_from = self.date_from_var.get().strip()
        raw_to = self.date_to_var.get().strip()
        date_from = date_to = None
        error = ""
        if raw_from:
            try:
                date_from = parse_date(raw_from).isoformat()
            except ValueError:
                error = "La fecha «Desde» no es válida. Usa dd/mm/aaaa."
        if not error and raw_to:
            try:
                date_to = parse_date(raw_to).isoformat()
            except ValueError:
                error = "La fecha «Hasta» no es válida. Usa dd/mm/aaaa."
        if not error and date_from and date_to and date_from > date_to:
            error = "«Desde» no puede ser posterior a «Hasta»."
        if error:
            self.range_hint.configure(text=error, fg=theme.RED)
        else:
            self.range_hint.configure(
                text="Rango de fechas opcional (dd/mm/aaaa). Búsqueda avanzada: "
                     "monto>100 · categoria:Ocio · cuenta:Efectivo · tipo:egreso · "
                     "fecha:2026-11.",
                fg=theme.SUBTLE,
            )
        self._date_from = None if error else date_from
        self._date_to = None if error else date_to

    def _filters(self, paginate: bool = True) -> dict:
        filters: dict = {}
        text = self.search_var.get().strip()
        if text:
            filters["text"] = text
        kind = KIND_FILTERS.get(self.kind_var.get())
        if kind:
            filters["kind"] = kind
        category_id = self.cat_map.get(self.cat_var.get())
        if category_id is not None:
            filters["category_id"] = category_id
        account_id = self.acc_map.get(self.acc_var.get())
        if account_id:
            filters["account_id"] = account_id
        if self._date_from:
            filters["date_from"] = self._date_from
        if self._date_to:
            filters["date_to"] = self._date_to
        filters["sort"] = SORT_KEYS.get(self.sort_column, "fecha")
        filters["desc"] = self.sort_desc
        if paginate:
            filters["limit"] = PAGE_SIZE
            filters["offset"] = self.page * PAGE_SIZE
        return filters

    def _sort_by(self, column: str):
        if column not in SORT_KEYS:
            return
        if column == self.sort_column:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_column = column
            self.sort_desc = DEFAULT_DESC.get(column, False)
        self.page = 0
        self.refresh()

    def _change_page(self, delta: int):
        if self.page + delta < 0:
            return
        self.page += delta
        self.refresh()

    # ------------------------------------------------------------ datos
    def refresh(self):
        self._refresh_category_filter()
        if not self._restored_filters:
            self._restore_filter_selections()
        self._parse_dates()

        for item in self.tree.get_children():
            self.tree.delete(item)

        base_filters = self._filters(paginate=False)
        totals = self.db.transaction_totals(base_filters)
        count = totals["count"]
        pages = max(1, (count + PAGE_SIZE - 1) // PAGE_SIZE)
        if self.page >= pages:
            self.page = pages - 1

        rows = self.db.transactions(dict(base_filters, limit=PAGE_SIZE,
                                         offset=self.page * PAGE_SIZE))

        for tx in rows:
            if tx["kind"] == "transferencia":
                category = "Transferencia"
                account = " → ".join(filter(None, [
                    tx["account_name"], tx["transfer_account_name"]
                ])) or "—"
                description = tx["description"] or "Entre cuentas"
                if tx.get("transfer_amount"):
                    amount_text = (
                        f"{self.money_native(tx['amount'], tx.get('account_currency'), date=tx['date'])}"
                        f" → {self.money_native(tx['transfer_amount'], tx.get('transfer_currency'), date=tx['date'])}"
                    )
                else:
                    amount_text = self.money_native(
                        tx["amount"], tx.get("account_currency"), date=tx["date"]
                    )
            else:
                category = tx["category_name"] or "Sin categoría"
                account = tx["account_name"] or "—"
                description = tx["description"] or category
                amount_text = self.money_native(
                    tx["amount"], tx.get("account_currency"), date=tx["date"]
                )
            self.tree.insert("", "end", iid=str(tx["id"]), tags=(tx["kind"],), values=(
                fmt_date(tx["date"]),
                KIND_LABELS.get(tx["kind"], tx["kind"]),
                truncate(description, 60),
                truncate(category, 28),
                truncate(account, 32),
                amount_text,
            ))

        self.lbl_count.configure(text=f"{count} movimiento{'s' if count != 1 else ''}")
        self.lbl_income.configure(text=self.money(totals["income"]))
        self.lbl_expense.configure(text=self.money(totals["expense"]))
        net = totals["income"] - totals["expense"]
        self.lbl_net.configure(text=self.money(net), fg=self.app.color_for(net))

        has_filter = any(key not in ("sort", "desc") for key in base_filters)
        if rows:
            self.empty_lbl.place_forget()
        else:
            self.empty_lbl.configure(
                text="Ningún movimiento coincide con los filtros."
                if has_filter else
                "Todavía no hay movimientos. Usa «+ Nuevo movimiento» para registrar el primero."
            )
            self.empty_lbl.place(relx=0.5, rely=0.45, anchor="center")
            self.empty_lbl.lift()

        start = self.page * PAGE_SIZE + 1
        end = self.page * PAGE_SIZE + len(rows)
        self.range_lbl.configure(
            text=f"Mostrando {start}–{end} de {count}" if rows else "Sin resultados"
        )
        self.page_lbl.configure(text=f"Página {self.page + 1} de {pages}")
        self.btn_prev.configure(state="normal" if self.page > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.page + 1 < pages else "disabled")

        notes = []
        if self.app.display_currency:
            notes.append(
                f"Montos convertidos a {self.app.display_currency}: cada movimiento "
                "usa la tasa de su fecha y los totales la tasa actual."
            )
        elif self.db.has_foreign_accounts():
            notes.append(f"Los totales están consolidados en {self.app.base_currency}.")
        if count > len(rows) and not has_filter:
            notes.append("Usa las flechas de página para recorrer todo el historial "
                         "o los filtros para acotar la búsqueda.")
        self.note_lbl.configure(text=" ".join(notes))

        self._refresh_headings()
        self._save_filters()
        self._on_select()

    def _refresh_headings(self):
        for col, label, _width, anchor, _stretch in COLUMNS:
            arrow = ""
            if col == self.sort_column:
                arrow = " ▼" if self.sort_desc else " ▲"
            self.tree.heading(col, text=label + arrow, anchor=anchor,
                              command=lambda c=col: self._sort_by(c))

    def _on_select(self, _event=None):
        has_selection = bool(self.tree.selection())
        state = "normal" if has_selection else "disabled"
        self.btn_edit.configure(state=state)
        self.btn_delete.configure(state=state)

    # ------------------------------------------------------------ acciones
    def _selected_id(self) -> int | None:
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def _show_menu(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self.menu.tk_popup(event.x_root, event.y_root)

    def _edit(self):
        tx_id = self._selected_id()
        if not tx_id:
            return
        tx = self.db.get_transaction(tx_id)
        if not tx:
            self.refresh()
            return
        if TransactionDialog(self, self.db, tx=tx).run():
            self._after_change()

    def _delete(self):
        tx_id = self._selected_id()
        if not tx_id:
            return
        tx = self.db.get_transaction(tx_id)
        if not tx:
            self.refresh()
            return
        if not ask_confirm(self, "Eliminar movimiento",
                           "¿Seguro que quieres eliminar este movimiento? "
                           "Podrás recuperarlo con «Deshacer»."):
            return
        db = self.db
        db.delete_transaction(tx_id)
        entry = self.app.push_undo("eliminar movimiento",
                                   lambda: db.restore_transaction(tx))
        self._after_change()
        self.app.toast("Movimiento eliminado", action_text="Deshacer",
                       action=lambda: self.app.undo_entry(entry))

    def _after_change(self):
        self.refresh()
        self.app.update_sidebar()

    def _export(self):
        path = filedialog.asksaveasfilename(
            parent=self, title="Exportar movimientos",
            defaultextension=".csv", filetypes=[("Archivo CSV", "*.csv")],
            initialfile=f"movimientos_{dt.date.today():%Y%m%d}.csv",
        )
        if not path:
            return
        self._parse_dates()
        try:
            count = self.db.export_csv(path, self._filters(paginate=False))
        except OSError as exc:
            self.app.toast(f"No se pudo exportar: {exc}", "error")
            return
        self.app.toast(f"{count} movimientos exportados")

    def focus_search(self):
        self.search_entry.focus_set()

    def destroy(self):
        if self._search_job:
            try:
                self.after_cancel(self._search_job)
            except tk.TclError:
                pass
            self._search_job = None
        super().destroy()
