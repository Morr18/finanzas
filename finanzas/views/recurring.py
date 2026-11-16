"""Movimientos recurrentes: reglas de ingreso, egreso y transferencia."""
from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import ttk

from .. import theme
from ..dialogs import RecurringDialog, ask_confirm
from ..theme import font
from ..utils import fmt_date, month_bounds, month_key, recurring_schedule_text, truncate
from ..widgets import Card
from . import BaseView

COLUMNS = (
    ("desc", "Descripción", 240, "w", True),
    ("freq", "Frecuencia", 170, "w", False),
    ("next", "Próximo", 100, "w", False),
    ("account", "Cuenta", 210, "w", False),
    ("amount", "Monto", 130, "e", False),
    ("status", "Estado", 90, "w", False),
)


class RecurringView(BaseView):
    title = "Recurrentes"
    subtitle = "Movimientos que se registran solos al abrir la aplicación"

    def __init__(self, app):
        super().__init__(app)
        self._build()
        self.refresh()

    def _build(self):
        top = Card(self, padding=16)
        top.pack(fill="x")
        head = tk.Frame(top.inner, bg=theme.CARD)
        head.pack(fill="x")
        left = tk.Frame(head, bg=theme.CARD)
        left.pack(side="left")
        tk.Label(left, text="MOVIMIENTOS RECURRENTES", bg=theme.CARD, fg=theme.MUTED,
                 font=font(8, "bold")).pack(anchor="w")
        self.summary_lbl = tk.Label(left, text="", bg=theme.CARD, fg=theme.TEXT,
                                    font=font(18, "bold"))
        self.summary_lbl.pack(anchor="w", pady=(2, 0))
        self.hint_lbl = tk.Label(left, text="", bg=theme.CARD, fg=theme.MUTED,
                                 font=font(9))
        self.hint_lbl.pack(anchor="w")

        ttk.Button(head, text="+ Nuevo recurrente", style="Primary.TButton",
                   command=self._new).pack(side="right")
        ttk.Button(head, text="Generar pendientes", style="Secondary.TButton",
                   command=self._generate).pack(side="right", padx=(0, 8))

        table_card = Card(self, padding=16)
        table_card.pack(fill="both", expand=True, pady=(14, 0))
        holder = tk.Frame(table_card.inner, bg=theme.CARD)
        holder.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(holder, columns=[c[0] for c in COLUMNS],
                                 show="headings", selectmode="browse")
        for col, label, width, anchor, stretch in COLUMNS:
            self.tree.heading(col, text=label, anchor=anchor)
            self.tree.column(col, width=width, anchor=anchor, stretch=stretch, minwidth=60)
        vsb = ttk.Scrollbar(holder, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.empty_lbl = tk.Label(
            holder,
            text="Todavía no hay movimientos recurrentes.\n"
                 "Crea uno para registrar el alquiler, las suscripciones o tu ahorro mensual.",
            bg=theme.CARD, fg=theme.SUBTLE, font=font(10), justify="center",
            wraplength=520,
        )
        self.tree.tag_configure("inactive", foreground=theme.SUBTLE)
        self.tree.tag_configure("transfer", foreground=theme.BLUE_DARK)
        self.tree.bind("<Double-1>", lambda _e: self._edit())
        self.tree.bind("<Delete>", lambda _e: self._delete())
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        footer = tk.Frame(table_card.inner, bg=theme.CARD)
        footer.pack(fill="x", pady=(10, 0))
        self.btn_edit = ttk.Button(footer, text="Editar", style="Secondary.TButton",
                                   command=self._edit, state="disabled")
        self.btn_edit.pack(side="left")
        self.btn_toggle = ttk.Button(footer, text="Pausar", style="Ghost.TButton",
                                     command=self._toggle, state="disabled")
        self.btn_toggle.pack(side="left", padx=6)
        self.btn_delete = ttk.Button(footer, text="Eliminar", style="DangerLink.TButton",
                                     command=self._delete, state="disabled")
        self.btn_delete.pack(side="left")
        self.footer_hint = tk.Label(
            footer,
            text="Los movimientos ya generados se conservan si eliminas la regla.",
            bg=theme.CARD, fg=theme.SUBTLE, font=font(8), anchor="e",
        )
        self.footer_hint.pack(side="right")

    # ------------------------------------------------------------ datos
    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        rules = self.db.recurring()
        active = [r for r in rules if r.get("active")]
        _, month_end = month_bounds(month_key())
        pending = 0
        for rule in active:
            next_date = self.db.next_occurrence(rule)
            if next_date and next_date <= month_end:
                pending += 1
        self.summary_lbl.configure(
            text=f"{len(rules)} regla{'s' if len(rules) != 1 else ''}"
        )
        self.hint_lbl.configure(
            text=f"{len(active)} activa{'s' if len(active) != 1 else ''} · "
                 f"{pending} pendiente{'s' if pending != 1 else ''} este mes"
        )

        for rule in rules:
            description = (rule.get("description") or "").strip()
            if not description:
                if rule["kind"] == "transferencia":
                    description = "Transferencia recurrente"
                else:
                    description = rule.get("category_name") or "Movimiento recurrente"
            if rule["kind"] == "transferencia":
                account = " → ".join(filter(None, [
                    rule.get("account_name"), rule.get("transfer_account_name")
                ])) or "—"
            else:
                account = rule.get("account_name") or "—"
            next_date = self.db.next_occurrence(rule) if rule.get("active") else None
            tags = []
            if not rule.get("active"):
                tags.append("inactive")
            if rule["kind"] == "transferencia":
                tags.append("transfer")
            self.tree.insert("", "end", iid=str(rule["id"]), tags=tuple(tags), values=(
                truncate(description, 48),
                recurring_schedule_text(rule),
                fmt_date(next_date) if next_date else "—",
                truncate(account, 40),
                self.money_native(rule["amount"], rule.get("account_currency"),
                                  date=next_date or month_key() + "-01"),
                "Activa" if rule.get("active") else "Pausada",
            ))

        if rules:
            self.empty_lbl.place_forget()
        else:
            self.empty_lbl.place(relx=0.5, rely=0.45, anchor="center")
            self.empty_lbl.lift()
        self._on_select()

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        state = "normal" if selection else "disabled"
        self.btn_edit.configure(state=state)
        self.btn_delete.configure(state=state)
        self.btn_toggle.configure(state=state)
        if selection:
            rule = self.db.get_recurring(int(selection[0]))
            self.btn_toggle.configure(text="Pausar" if rule and rule.get("active")
                                      else "Activar")
        else:
            self.btn_toggle.configure(text="Pausar")

    def _selected_id(self) -> int | None:
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def _after_change(self):
        self.refresh()
        self.app.update_sidebar()

    # ------------------------------------------------------------ acciones
    def _new(self):
        if RecurringDialog(self, self.db).run():
            created = self.app.process_recurring(notify=False, refresh=False)
            self._after_change()
            if created:
                self.app.toast(
                    f"Recurrente creado · {created} movimiento"
                    f"{'s' if created != 1 else ''} generado{'s' if created != 1 else ''}"
                )
            else:
                self.app.toast("Movimiento recurrente creado")

    def _edit(self):
        rule_id = self._selected_id()
        if not rule_id:
            return
        rule = self.db.get_recurring(rule_id)
        if not rule:
            self.refresh()
            return
        if RecurringDialog(self, self.db, rule=rule).run():
            created = self.app.process_recurring(notify=False, refresh=False)
            self._after_change()
            if created:
                self.app.toast(
                    f"Recurrente actualizado · {created} movimiento"
                    f"{'s' if created != 1 else ''} generado{'s' if created != 1 else ''}"
                )
            else:
                self.app.toast("Recurrente actualizado")

    def _delete(self):
        rule_id = self._selected_id()
        if not rule_id:
            return
        rule = self.db.get_recurring(rule_id)
        if not rule:
            self.refresh()
            return
        if not ask_confirm(
            self, "Eliminar recurrente",
            "¿Eliminar esta regla recurrente? Los movimientos que ya se generaron "
            "se conservarán. Podrás recuperar la regla con «Deshacer».",
        ):
            return
        db = self.db
        row = dict(rule)
        db.delete_recurring(rule_id)
        self._after_change()
        self.app.undo_toast(
            "Recurrente eliminado", "eliminar recurrente",
            lambda: db.restore_recurring(row),
        )

    def _toggle(self):
        rule_id = self._selected_id()
        if not rule_id:
            return
        rule = self.db.get_recurring(rule_id)
        if not rule:
            return
        make_active = not bool(rule.get("active"))
        self.db.set_recurring_active(rule_id, make_active)
        created = 0
        if make_active:
            created = self.app.process_recurring(notify=False, refresh=False)
        self._after_change()
        self.app.toast(
            f"Recurrente {'activado' if make_active else 'pausado'}"
            + (f" · {created} movimiento{'s' if created != 1 else ''} generado"
               f"{'s' if created != 1 else ''}" if created else "")
        )

    def _generate(self):
        self.app.process_recurring(notify=True, manual=True)
        self.refresh()
