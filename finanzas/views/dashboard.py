"""Panel principal: resumen del mes, gráficas y últimos movimientos."""
from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import ttk

from .. import theme
from ..theme import font
from ..utils import fmt_date_short, month_bounds, month_key, month_name, pct_text, truncate
from ..widgets import (
    BarChart, Card, DonutChart, EmptyState, ProgressBar, ScrollFrame, StatCard,
    card_title, legend_row,
)
from . import BaseView


class DashboardView(BaseView):
    title = "Resumen"
    subtitle = "Tu panorama financiero de un vistazo"

    def __init__(self, app):
        super().__init__(app)
        self.scroll = ScrollFrame(self, bg=theme.BG)
        self.scroll.pack(fill="both", expand=True)
        body = self.scroll.body
        body.columnconfigure(0, weight=1)
        self.body = body

        self.main = tk.Frame(body, bg=theme.BG)
        self.main.grid(row=0, column=0, sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self.welcome: tk.Frame | None = None
        self._build_main()

    # ------------------------------------------------------------ estructura
    def _build_main(self):
        stats = tk.Frame(self.main, bg=theme.BG)
        stats.grid(row=0, column=0, sticky="ew")
        for i in range(4):
            stats.columnconfigure(i, weight=1, uniform="stat")
        self.card_balance = StatCard(stats, "Balance total", accent=theme.PRIMARY)
        self.card_income = StatCard(stats, "Ingresos del mes", accent=theme.GREEN)
        self.card_expense = StatCard(stats, "Egresos del mes", accent=theme.RED)
        self.card_saving = StatCard(stats, "Ahorro del mes", accent=theme.BLUE)
        for i, card in enumerate((self.card_balance, self.card_income,
                                  self.card_expense, self.card_saving)):
            card.grid(row=0, column=i, sticky="nsew",
                      padx=(0 if i == 0 else 6, 0 if i == 3 else 6))

        charts = tk.Frame(self.main, bg=theme.BG)
        charts.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        charts.columnconfigure(0, weight=3, uniform="chart")
        charts.columnconfigure(1, weight=2, uniform="chart")

        flow_card = Card(charts, padding=16)
        flow_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        card_title(flow_card.inner, "Flujo de caja",
                   "Ingresos y egresos de los últimos 6 meses").pack(fill="x")
        self.chart = BarChart(flow_card.inner, height=225, symbol=self.app.currency)
        self.chart.pack(fill="both", expand=True, pady=(10, 0))

        donut_card = Card(charts, padding=16)
        donut_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(donut_card.inner, text="Gastos por categoría", bg=theme.CARD,
                 fg=theme.TEXT, font=font(11, "bold"), anchor="w").pack(fill="x")
        self.donut_sub = tk.Label(donut_card.inner, text=month_name(month_key()),
                                  bg=theme.CARD, fg=theme.MUTED, font=font(9),
                                  anchor="w")
        self.donut_sub.pack(fill="x", pady=(2, 0))
        content = tk.Frame(donut_card.inner, bg=theme.CARD)
        content.pack(fill="both", expand=True, pady=(8, 0))
        self.donut = DonutChart(content, size=158, symbol=self.app.currency)
        self.donut.pack(side="left", padx=(0, 10))
        self.legend = tk.Frame(content, bg=theme.CARD)
        self.legend.pack(side="left", fill="both", expand=True)

        bottom = tk.Frame(self.main, bg=theme.BG)
        bottom.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        bottom.columnconfigure(0, weight=3, uniform="b")
        bottom.columnconfigure(1, weight=2, uniform="b")

        recent_card = Card(bottom, padding=16)
        recent_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        head = tk.Frame(recent_card.inner, bg=theme.CARD)
        head.pack(fill="x")
        card_title(head, "Últimos movimientos").pack(side="left")
        ttk.Button(head, text="Ver todos", style="Link.TButton",
                   command=lambda: self.app.show("movimientos")).pack(side="right")
        self.recent = ttk.Treeview(
            recent_card.inner, columns=("fecha", "desc", "cat", "monto"),
            show="headings", height=5, selectmode="none",
        )
        for col, label, width, anchor in (
            ("fecha", "Fecha", 70, "w"), ("desc", "Descripción", 190, "w"),
            ("cat", "Categoría", 120, "w"), ("monto", "Monto", 110, "e"),
        ):
            self.recent.heading(col, text=label, anchor=anchor)
            self.recent.column(col, width=width, anchor=anchor,
                               stretch=(col == "desc"))
        self.recent.pack(fill="both", expand=True, pady=(10, 0))

        budget_card = Card(bottom, padding=16)
        budget_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        head = tk.Frame(budget_card.inner, bg=theme.CARD)
        head.pack(fill="x")
        card_title(head, "Presupuestos del mes").pack(side="left")
        ttk.Button(head, text="Gestionar", style="Link.TButton",
                   command=lambda: self.app.show("presupuestos")).pack(side="right")
        self.budget_holder = tk.Frame(budget_card.inner, bg=theme.CARD)
        self.budget_holder.pack(fill="both", expand=True, pady=(10, 0))

    def _build_welcome(self):
        self.welcome = tk.Frame(self.body, bg=theme.BG)
        self.welcome.grid(row=0, column=0, sticky="nsew")
        card = Card(self.welcome, padding=26)
        card.pack(fill="x", pady=(40, 0))
        EmptyState(
            card.inner,
            "Bienvenido a Finanzas",
            "Registra tus ingresos y egresos para ver tu balance, tus gastos por categoría "
            "y el avance de tus presupuestos. Todo se guarda localmente en tu equipo.",
            glyph="◎",
            action=self.app.new_transaction,
            action_text="Registrar mi primer movimiento",
            secondary=self.app.load_demo_data,
            secondary_text="Cargar datos de ejemplo",
        ).pack(pady=10)

    # ------------------------------------------------------------ datos
    def refresh(self):
        if not self.db.has_transactions():
            self.main.grid_remove()
            if self.welcome is None:
                self._build_welcome()
            self.welcome.grid()
            return

        if self.welcome is not None:
            self.welcome.grid_remove()
        self.main.grid()

        today = dt.date.today()
        key = month_key(today)
        start, end = month_bounds(key)
        summary = self.db.summary(start, end)
        accounts = self.db.account_balances()
        total = sum(a["base_balance"] for a in accounts)

        balance_hint = f"En {len(accounts)} cuenta{'s' if len(accounts) != 1 else ''}"
        if self.app.display_currency:
            balance_hint += f" · en {self.app.display_currency}"
        elif self.db.has_foreign_accounts():
            balance_hint += f" · base {self.app.base_currency}"
        self.card_balance.set_values(
            self.money(total), balance_hint,
            color=self.app.color_for(total),
        )
        self.card_income.set_values(self.money(summary["income"]),
                                month_name(key), color=theme.GREEN)
        expense_hint = (pct_text(summary["expense"], summary["income"]) + " del ingreso"
                        if summary["income"] else "sin ingresos registrados")
        self.card_expense.set_values(self.money(summary["expense"]), expense_hint, color=theme.RED)

        net = summary["net"]
        rate = (net / summary["income"] * 100) if summary["income"] else 0
        self.card_saving.set_values(
            self.money(net), f"Tasa de ahorro {rate:.0f}%",
            color=theme.GREEN if net >= 0 else theme.RED,
            hint_color=theme.MUTED,
        )

        self.donut_sub.configure(text=month_name(key))
        series = [
            {
                "key": row["key"],
                "income": self.convert_display(row["income"]),
                "expense": self.convert_display(row["expense"]),
            }
            for row in self.db.monthly_series(6)
        ]
        self.chart.set_data(series, symbol=self.app.display_symbol(),
                            style=self.app.number_format)
        self._refresh_donut(start, end, key)
        self._refresh_recent()
        self._refresh_budgets(key)

    def _refresh_donut(self, start: str, end: str, key: str):
        totals = self.db.category_totals("egreso", start, end)
        total = sum(item["total"] for item in totals)
        top = totals[:5]
        if len(totals) > 5:
            others = sum(item["total"] for item in totals[5:])
            top.append({"name": "Otros", "total": others, "color": "#94a3b8"})

        self.donut.set_data(
            [(item["name"], item["total"], item["color"]) for item in top],
            self.money(total) if total else "", "Gastos",
            symbol=self.app.display_symbol(),
        )
        for child in self.legend.winfo_children():
            child.destroy()
        if not top:
            tk.Label(self.legend, text="Sin gastos\nregistrados este mes", bg=theme.CARD,
                     fg=theme.SUBTLE, font=font(9), justify="left").pack(anchor="w")
            return
        for item in top:
            legend_row(self.legend, item["color"], item["name"],
                       self.money(item["total"]), max_label=14).pack(fill="x", pady=3)

    def _refresh_recent(self):
        for item in self.recent.get_children():
            self.recent.delete(item)
        self.recent.tag_configure("ingreso", background=theme.GREEN_SOFT,
                                  foreground=theme.GREEN_DARK)
        self.recent.tag_configure("egreso", background=theme.RED_SOFT,
                                  foreground=theme.RED_DARK)
        self.recent.tag_configure("transferencia", background=theme.BLUE_SOFT,
                                  foreground=theme.BLUE_DARK)
        for tx in self.db.transactions({"limit": 5}):
            if tx["kind"] == "transferencia":
                category = "Transferencia"
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
                description = tx["description"] or category
                amount_text = self.money_native(
                    tx["amount"], tx.get("account_currency"), date=tx["date"]
                )
            self.recent.insert("", "end", tags=(tx["kind"],), values=(
                fmt_date_short(tx["date"]), truncate(description, 30),
                truncate(category, 18), amount_text,
            ))

    def _refresh_budgets(self, key: str):
        for child in self.budget_holder.winfo_children():
            child.destroy()
        rows = self.db.budgets_for_month(key)
        rows = [r for r in rows if r["budget"] > 0]
        if not rows:
            tk.Label(self.budget_holder, text="Aún no defines presupuestos mensuales.",
                     bg=theme.CARD, fg=theme.SUBTLE, font=font(9), anchor="w",
                     justify="left", wraplength=260).pack(fill="x", pady=(2, 8))
            ttk.Button(self.budget_holder, text="Definir presupuestos",
                       style="Secondary.TButton",
                       command=lambda: self.app.show("presupuestos")).pack(anchor="w")
            return

        total_budget = sum(r["budget"] for r in rows)
        total_spent = sum(r["spent"] for r in rows)
        top = tk.Frame(self.budget_holder, bg=theme.CARD)
        top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text=f"{self.money(total_spent)} de {self.money(total_budget)}",
                 bg=theme.CARD, fg=theme.TEXT, font=font(9, "bold")).pack(side="left")
        tk.Label(top, text=pct_text(total_spent, total_budget), bg=theme.CARD,
                 fg=theme.MUTED, font=font(9)).pack(side="right")

        for row in rows[:4]:
            holder = tk.Frame(self.budget_holder, bg=theme.CARD)
            holder.pack(fill="x", pady=4)
            ratio = row["spent"] / row["budget"] if row["budget"] else 0
            color = theme.GREEN if ratio < 0.7 else theme.AMBER if ratio <= 1 else theme.RED
            line = tk.Frame(holder, bg=theme.CARD)
            line.pack(fill="x")
            tk.Label(line, text=truncate(row["name"], 22), bg=theme.CARD, fg=theme.TEXT,
                     font=font(9), anchor="w").pack(side="left")
            tk.Label(line, text=pct_text(row["spent"], row["budget"]), bg=theme.CARD,
                     fg=color, font=font(9, "bold")).pack(side="right")
            bar = ProgressBar(holder, height=7, bg=theme.CARD)
            bar.pack(fill="x", pady=(4, 0))
            bar.set(ratio * 100, color)
