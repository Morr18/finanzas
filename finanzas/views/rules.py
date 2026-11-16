"""Reglas automáticas para categorizar y asignar cuentas."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import theme
from ..dialogs import RuleDialog, ask_confirm
from ..theme import font
from ..utils import truncate
from ..widgets import Card
from . import BaseView

COLUMNS = (
    ("match", "Si la descripción contiene", 260, "w", True),
    ("category", "Categoría", 190, "w", False),
    ("account", "Cuenta", 190, "w", False),
    ("status", "Estado", 90, "w", False),
)


class RulesView(BaseView):
    title = "Reglas"
    subtitle = "Categoriza y asigna cuentas automáticamente al crear movimientos"

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
        tk.Label(left, text="REGLAS AUTOMÁTICAS", bg=theme.CARD, fg=theme.MUTED,
                 font=font(8, "bold")).pack(anchor="w")
        self.summary_lbl = tk.Label(left, text="", bg=theme.CARD, fg=theme.TEXT,
                                    font=font(18, "bold"))
        self.summary_lbl.pack(anchor="w", pady=(2, 0))
        self.hint_lbl = tk.Label(
            left,
            text="Se aplican al crear un movimiento, comparando descripción y notas "
                 "sin distinguir mayúsculas.",
            bg=theme.CARD, fg=theme.MUTED, font=font(9),
        )
        self.hint_lbl.pack(anchor="w")

        ttk.Button(head, text="+ Nueva regla", style="Primary.TButton",
                   command=self._new).pack(side="right")
        ttk.Button(head, text="Aplicar a existentes", style="Secondary.TButton",
                   command=self._apply_existing).pack(side="right", padx=(0, 8))

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
            text="Todavía no hay reglas.\n"
                 "Ejemplo: si la descripción contiene NETFLIX, asigna la categoría Ocio "
                 "y la cuenta de la tarjeta.",
            bg=theme.CARD, fg=theme.SUBTLE, font=font(10), justify="center",
            wraplength=540,
        )
        self.tree.tag_configure("inactive", foreground=theme.SUBTLE)
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
        tk.Label(
            footer,
            text="Solo se aplican a ingresos y egresos; nunca a transferencias.",
            bg=theme.CARD, fg=theme.SUBTLE, font=font(8), anchor="e",
        ).pack(side="right")

    # ------------------------------------------------------------ datos
    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        rules = self.db.rules()
        active = [r for r in rules if r.get("active")]
        self.summary_lbl.configure(
            text=f"{len(rules)} regla{'s' if len(rules) != 1 else ''}"
        )
        self.hint_lbl.configure(
            text=f"{len(active)} activa{'s' if len(active) != 1 else ''}. "
                 "Se aplican al crear un movimiento, comparando descripción y notas "
                 "sin distinguir mayúsculas."
        )
        for rule in rules:
            self.tree.insert("", "end", iid=str(rule["id"]),
                             tags=() if rule.get("active") else ("inactive",),
                             values=(
                                 truncate(rule.get("match_text") or "", 50),
                                 truncate(rule.get("category_name") or "No cambiar", 30),
                                 truncate(rule.get("account_name") or "No cambiar", 30),
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
            rule = self.db.get_rule(int(selection[0]))
            self.btn_toggle.configure(text="Pausar" if rule and rule.get("active")
                                      else "Activar")
        else:
            self.btn_toggle.configure(text="Pausar")

    def _selected_id(self) -> int | None:
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    # ------------------------------------------------------------ acciones
    def _new(self):
        if RuleDialog(self, self.db).run():
            self.refresh()
            self.app.toast("Regla creada")

    def _edit(self):
        rule_id = self._selected_id()
        if not rule_id:
            return
        rule = self.db.get_rule(rule_id)
        if not rule:
            self.refresh()
            return
        if RuleDialog(self, self.db, rule=rule).run():
            self.refresh()
            self.app.toast("Regla actualizada")

    def _delete(self):
        rule_id = self._selected_id()
        if not rule_id:
            return
        rule = self.db.get_rule(rule_id)
        if not rule:
            self.refresh()
            return
        if not ask_confirm(
            self, "Eliminar regla",
            "¿Eliminar esta regla? Los movimientos ya registrados no cambiarán. "
            "Podrás recuperarla con «Deshacer».",
        ):
            return
        db = self.db
        row = dict(rule)
        db.delete_rule(rule_id)
        self.refresh()
        self.app.undo_toast(
            "Regla eliminada", "eliminar regla",
            lambda: db.restore_rule(row),
        )

    def _toggle(self):
        rule_id = self._selected_id()
        if not rule_id:
            return
        rule = self.db.get_rule(rule_id)
        if not rule:
            return
        make_active = not bool(rule.get("active"))
        self.db.set_rule_active(rule_id, make_active)
        self.refresh()
        self.app.toast(f"Regla {'activada' if make_active else 'pausada'}")

    def _apply_existing(self):
        if not self.db.rules(include_inactive=False):
            self.app.toast("No hay reglas activas para aplicar", "info")
            return
        if not ask_confirm(
            self, "Aplicar reglas a movimientos existentes",
            "Se cambiarán la categoría y/o la cuenta de los movimientos que coincidan "
            "con las reglas activas. Las transferencias no se modifican. "
            "Esta acción no se puede deshacer. ¿Continuar?",
            confirm_text="Aplicar reglas", danger=False,
        ):
            return
        changed = self.db.apply_rules_to_existing()
        self.refresh()
        self.app.update_sidebar()
        self.app.toast(
            f"{changed} movimiento{'s' if changed != 1 else ''} actualizado"
            f"{'s' if changed != 1 else ''}"
        )
