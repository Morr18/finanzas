"""Presupuestos mensuales por categoría de gasto."""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

from .. import theme
from ..dialogs import ask_confirm
from ..theme import font
from ..utils import money_input, month_key, month_name, parse_amount, pct_text, shift_month, truncate
from ..widgets import Card, ProgressBar, ScrollFrame, StatCard, form_label
from . import BaseView


def _budget_cents(raw: str) -> int:
    """Cero (en cualquier formato) significa quitar el presupuesto."""
    text = (raw or "").strip().replace(" ", "")
    if not text or re.fullmatch(r"0+([.,]0+)?", text):
        return 0
    return parse_amount(text)


class BudgetsView(BaseView):
    title = "Presupuestos"
    subtitle = "Define límites mensuales por categoría y controla tus gastos"

    def __init__(self, app):
        super().__init__(app)
        self.key = month_key()
        self.entry_vars: dict[int, tuple[tk.StringVar, int, int, str]] = {}
        self._build()
        self.refresh()

    def _build(self):
        nav = Card(self, padding=12)
        nav.pack(fill="x")
        row = tk.Frame(nav.inner, bg=theme.CARD)
        row.pack(fill="x")
        ttk.Button(row, text="←", style="Secondary.TButton", width=3,
                   command=lambda: self._shift(-1)).pack(side="left")
        self.month_lbl = tk.Label(row, text="", bg=theme.CARD, fg=theme.TEXT,
                                  font=font(12, "bold"))
        self.month_lbl.pack(side="left", padx=14)
        ttk.Button(row, text="→", style="Secondary.TButton", width=3,
                   command=lambda: self._shift(1)).pack(side="left")
        ttk.Button(row, text="Mes actual", style="Link.TButton",
                   command=self._current_month).pack(side="right")

        stats = tk.Frame(self, bg=theme.BG)
        stats.pack(fill="x", pady=(14, 0))
        for i in range(3):
            stats.columnconfigure(i, weight=1, uniform="bst")
        self.card_budget = StatCard(stats, "Presupuesto total", accent=theme.PRIMARY)
        self.card_spent = StatCard(stats, "Gastado", accent=theme.RED)
        self.card_available = StatCard(stats, "Disponible", accent=theme.GREEN)
        for i, card in enumerate((self.card_budget, self.card_spent, self.card_available)):
            card.grid(row=0, column=i, sticky="nsew",
                      padx=(0 if i == 0 else 6, 0 if i == 2 else 6))

        card = Card(self, padding=16)
        card.pack(fill="both", expand=True, pady=(14, 0))
        head = tk.Frame(card.inner, bg=theme.CARD)
        head.pack(fill="x")
        tk.Label(head, text="Límites por categoría", bg=theme.CARD, fg=theme.TEXT,
                 font=font(11, "bold"), anchor="w").pack(side="left")
        ttk.Button(head, text="Guardar cambios", style="Primary.TButton",
                   command=self._save).pack(side="right")
        self.budget_note = tk.Label(
            card.inner,
            text="Deja un campo vacío o en cero para quitar el presupuesto. "
                 "Los límites se repiten cada mes.",
            bg=theme.CARD, fg=theme.MUTED, font=font(8), anchor="w",
        )
        self.budget_note.pack(fill="x", pady=(2, 8))

        self.rows_scroll = ScrollFrame(card.inner, bg=theme.CARD)
        self.rows_scroll.pack(fill="both", expand=True)
        self.rows_holder = self.rows_scroll.body

    # ------------------------------------------------------------ acciones
    def _conv_date(self) -> str:
        return f"{self.key}-01"

    def _is_dirty(self) -> bool:
        for var, _old_base, old_display, _name in self.entry_vars.values():
            raw = var.get().strip()
            try:
                new_value = _budget_cents(raw)
            except ValueError:
                return True
            if new_value != old_display:
                return True
        return False

    def confirm_leave(self) -> bool:
        if not self._is_dirty():
            return True
        return ask_confirm(
            self, "Cambios sin guardar",
            "Tienes cambios en los presupuestos que aún no has guardado. "
            "¿Quieres descartarlos?",
            confirm_text="Descartar cambios", danger=True,
        )

    def _shift(self, delta: int):
        if not self.confirm_leave():
            return
        self.key = shift_month(self.key, delta)
        self.refresh()

    def _current_month(self):
        if not self.confirm_leave():
            return
        self.key = month_key()
        self.refresh()

    def _save(self):
        changed = 0
        for category_id, (var, old_base, old_display, name) in self.entry_vars.items():
            raw = var.get().strip()
            try:
                new_display = _budget_cents(raw)
            except ValueError:
                self.app.toast(f"Monto inválido en «{name}». Usa por ejemplo 1500.00", "error")
                return
            if new_display != old_display:
                new_base = (self.app.to_base_display(new_display, self._conv_date())
                            if new_display else 0)
                if new_base != old_base:
                    self.db.set_budget(category_id, new_base)
                    changed += 1
        if changed:
            self.app.toast(f"{changed} presupuesto{'s' if changed != 1 else ''} actualizado"
                           f"{'s' if changed != 1 else ''}")
        else:
            self.app.toast("No había cambios por guardar", "info")
        self.refresh()
        self.app.update_sidebar()

    # ------------------------------------------------------------ datos
    def refresh(self):
        self.month_lbl.configure(text=month_name(self.key))
        note = ("Deja un campo vacío o en cero para quitar el presupuesto. "
                "Los límites se repiten cada mes.")
        if self.app.display_currency:
            note = (f"Los campos están en {self.app.display_currency}; se guardan "
                    f"convertidos a {self.app.base_currency}. " + note)
        self.budget_note.configure(text=note)
        rows = self.db.budgets_for_month(self.key)
        budgeted = [r for r in rows if r["budget"] > 0]
        total_budget = sum(r["budget"] for r in budgeted)
        spent = sum(r["spent"] for r in budgeted)
        available = total_budget - spent

        self.card_budget.set_values(
            self.money(total_budget),
            f"{len(budgeted)} de {len(rows)} categorías con límite",
        )
        self.card_spent.set_values(
            self.money(spent),
            pct_text(spent, total_budget) + " del presupuesto" if total_budget else "sin presupuesto",
            color=theme.RED,
        )
        self.card_available.set_values(
            self.money(available),
            "sobrepasado" if available < 0 else "disponible este mes",
            color=theme.GREEN if available >= 0 else theme.RED,
        )

        for child in self.rows_holder.winfo_children():
            child.destroy()
        self.entry_vars.clear()

        if not rows:
            tk.Label(self.rows_holder,
                     text="Crea categorías de gasto para asignarles un presupuesto.",
                     bg=theme.CARD, fg=theme.SUBTLE, font=font(9)).pack(pady=20)
            return

        header = tk.Frame(self.rows_holder, bg=theme.CARD)
        header.pack(fill="x", pady=(0, 4))
        form_label(header, "CATEGORÍA", theme.CARD).pack(side="left")
        budget_label = "PRESUPUESTO MENSUAL"
        if self.app.display_currency:
            budget_label += f" ({self.app.display_currency})"
        form_label(header, budget_label, theme.CARD).pack(side="right", padx=(0, 4))

        for index, item in enumerate(rows):
            self._build_row(item, index)

    def _build_row(self, item: dict, index: int):
        row = tk.Frame(self.rows_holder, bg=theme.CARD)
        row.pack(fill="x")
        row.columnconfigure(0, minsize=190)
        row.columnconfigure(1, weight=1)

        name_box = tk.Frame(row, bg=theme.CARD, width=190)
        name_box.grid(row=0, column=0, sticky="w", padx=(0, 14), pady=8)
        dot = tk.Canvas(name_box, width=10, height=10, bg=theme.CARD, highlightthickness=0)
        dot.create_oval(2, 2, 9, 9, fill=item["color"], outline="")
        dot.pack(side="left", padx=(0, 8))
        tk.Label(name_box, text=truncate(item["name"], 22), bg=theme.CARD, fg=theme.TEXT,
                 font=font(9, "bold")).pack(side="left")

        progress_box = tk.Frame(row, bg=theme.CARD)
        progress_box.grid(row=0, column=1, sticky="ew", pady=8)
        ratio = item["spent"] / item["budget"] if item["budget"] else 0
        color = theme.GREEN if ratio < 0.7 else theme.AMBER if ratio <= 1 else theme.RED

        if item["budget"]:
            text = f"{self.money(item['spent'])} de {self.money(item['budget'])}"
        else:
            text = f"Gastado {self.money(item['spent'])} · sin presupuesto"
        tk.Label(progress_box, text=text, bg=theme.CARD, fg=theme.MUTED, font=font(8),
                 anchor="w").pack(fill="x")
        bar = ProgressBar(progress_box, height=7, bg=theme.CARD)
        bar.pack(fill="x", pady=(4, 0))
        bar.set(min(ratio, 1) * 100, color)

        pct_lbl = tk.Label(row, text=pct_text(item["spent"], item["budget"]) if item["budget"] else "—",
                           bg=theme.CARD, fg=color if item["budget"] else theme.SUBTLE,
                           font=font(9, "bold"), width=5, anchor="e")
        pct_lbl.grid(row=0, column=2, padx=(12, 12))

        display_budget = self.convert_display(item["budget"], self._conv_date())
        var = tk.StringVar(value=money_input(display_budget, self.app.number_format))
        entry = ttk.Entry(row, textvariable=var, width=12, justify="right")
        entry.grid(row=0, column=3, sticky="e")
        self.entry_vars[item["id"]] = (
            var, item["budget"], display_budget, item["name"]
        )

        tk.Frame(self.rows_holder, bg=theme.BORDER, height=1).pack(fill="x")
