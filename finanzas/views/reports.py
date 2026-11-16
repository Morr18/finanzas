"""Reportes anuales: resumen mensual y gastos por categoría."""
from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import filedialog, ttk

from .. import theme
from ..theme import font
from ..utils import MESES, pct, pct_text, truncate
from ..widgets import Card, ProgressBar, ScrollFrame, StatCard, card_title
from . import BaseView


class ReportsView(BaseView):
    title = "Reportes"
    subtitle = "Compara meses y descubre en qué se va tu dinero"

    def __init__(self, app):
        super().__init__(app)
        self.year_var = tk.StringVar()
        self._build()
        self.refresh()

    def _build(self):
        self.scroll = ScrollFrame(self, bg=theme.BG)
        self.scroll.pack(fill="both", expand=True)
        body = self.scroll.body
        body.columnconfigure(0, weight=1)
        self.body = body

        controls = Card(body, padding=14)
        controls.grid(row=0, column=0, sticky="ew")
        row = tk.Frame(controls.inner, bg=theme.CARD)
        row.pack(fill="x")
        tk.Label(row, text="Año", bg=theme.CARD, fg=theme.MUTED,
                 font=font(9, "bold")).pack(side="left", padx=(0, 8))
        self.year_combo = ttk.Combobox(row, textvariable=self.year_var, state="readonly",
                                       width=8)
        self.year_combo.pack(side="left")
        self.year_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        self.currency_lbl = tk.Label(row, text="", bg=theme.CARD, fg=theme.MUTED,
                                     font=font(8), anchor="w")
        self.currency_lbl.pack(side="left", padx=10)
        ttk.Button(row, text="Exportar CSV del año", style="Secondary.TButton",
                   command=self._export).pack(side="right")

        stats = tk.Frame(body, bg=theme.BG)
        stats.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        for i in range(4):
            stats.columnconfigure(i, weight=1, uniform="rst")
        self.card_income = StatCard(stats, "Ingresos del año", accent=theme.GREEN)
        self.card_expense = StatCard(stats, "Egresos del año", accent=theme.RED)
        self.card_net = StatCard(stats, "Ahorro neto", accent=theme.BLUE)
        self.card_rate = StatCard(stats, "Tasa de ahorro", accent=theme.AMBER)
        for i, card in enumerate((self.card_income, self.card_expense,
                                  self.card_net, self.card_rate)):
            card.grid(row=0, column=i, sticky="nsew",
                      padx=(0 if i == 0 else 6, 0 if i == 3 else 6))

        table_card = Card(body, padding=16)
        table_card.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        card_title(table_card.inner, "Resumen mensual",
                   "Ingresos, egresos y ahorro de cada mes").pack(fill="x")
        holder = tk.Frame(table_card.inner, bg=theme.CARD)
        holder.pack(fill="x", pady=(10, 0))
        columns = ("mes", "ingresos", "egresos", "neto", "tasa")
        self.table = ttk.Treeview(holder, columns=columns, show="headings", height=13,
                                  selectmode="none")
        for col, label, width, anchor in (
            ("mes", "Mes", 160, "w"), ("ingresos", "Ingresos", 180, "e"),
            ("egresos", "Egresos", 180, "e"), ("neto", "Ahorro", 180, "e"),
            ("tasa", "Tasa", 100, "e"),
        ):
            self.table.heading(col, text=label, anchor=anchor)
            self.table.column(col, width=width, anchor=anchor, stretch=True)
        self.table.pack(fill="x")
        self.table.tag_configure("total", font=font(10, "bold"), background=theme.CARD_SOFT)
        self.table.tag_configure("negative", foreground=theme.RED)
        self.table.tag_configure("positive", foreground=theme.GREEN)

        breakdown_card = Card(body, padding=16)
        breakdown_card.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        self.breakdown_title = card_title(
            breakdown_card.inner, "Gastos por categoría", "Distribución del año"
        )
        self.breakdown_title.pack(fill="x")
        self.breakdown = tk.Frame(breakdown_card.inner, bg=theme.CARD)
        self.breakdown.pack(fill="x", pady=(12, 0))

    # ------------------------------------------------------------ datos
    def refresh(self):
        if self.app.display_currency:
            self.currency_lbl.configure(
                text=f"Montos convertidos a {self.app.display_currency} · "
                     f"{self.app.display_rate_text()}"
            )
        else:
            self.currency_lbl.configure(
                text=f"Montos en {self.app.base_currency}"
            )
        years = self.db.years_with_data()
        self.year_combo.configure(values=[str(y) for y in years])
        try:
            year = int(self.year_var.get())
        except ValueError:
            year = years[0] if years else dt.date.today().year
        if year not in years:
            year = years[0] if years else dt.date.today().year
        self.year_var.set(str(year))

        months = self.db.year_totals(year)
        total_income = sum(m["income"] for m in months)
        total_expense = sum(m["expense"] for m in months)
        net = total_income - total_expense
        rate = (net / total_income * 100) if total_income else 0

        self.card_income.set_values(self.money(total_income), f"Año {year}", color=theme.GREEN)
        self.card_expense.set_values(self.money(total_expense),
                                 pct_text(total_expense, total_income) + " de los ingresos"
                                 if total_income else "sin ingresos",
                                 color=theme.RED)
        self.card_net.set_values(self.money(net), "ingresos menos egresos",
                             color=self.app.color_for(net))
        self.card_rate.set_values(f"{rate:.0f}%", "de tus ingresos",
                                  color=theme.GREEN if rate >= 0 else theme.RED)

        for item in self.table.get_children():
            self.table.delete(item)
        for month in months:
            self.table.insert("", "end", values=(
                MESES[month["month"] - 1],
                self.money(month["income"]),
                self.money(month["expense"]),
                self.money(month["net"]),
                pct_text(month["net"], month["income"]) if month["income"] else "—",
            ), tags=("negative",) if month["net"] < 0 else ())
        self.table.insert("", "end", values=(
            "Total del año", self.money(total_income), self.money(total_expense),
            self.money(net), pct_text(net, total_income) if total_income else "—",
        ), tags=("total",))

        self._refresh_breakdown(year, total_expense)

    def _refresh_breakdown(self, year: int, total_expense: int):
        for child in self.breakdown.winfo_children():
            child.destroy()
        rows = self.db.category_totals(
            "egreso", f"{year:04d}-01-01", f"{year:04d}-12-31"
        )
        if not rows:
            tk.Label(self.breakdown, text="Sin gastos registrados en este año.",
                     bg=theme.CARD, fg=theme.SUBTLE, font=font(9)).pack(anchor="w")
            return
        for item in rows:
            row = tk.Frame(self.breakdown, bg=theme.CARD)
            row.pack(fill="x", pady=5)
            row.columnconfigure(1, weight=1)

            name_box = tk.Frame(row, bg=theme.CARD)
            name_box.grid(row=0, column=0, sticky="w", padx=(0, 12))
            dot = tk.Canvas(name_box, width=10, height=10, bg=theme.CARD,
                            highlightthickness=0)
            dot.create_oval(2, 2, 9, 9, fill=item["color"], outline="")
            dot.pack(side="left", padx=(0, 7))
            tk.Label(name_box, text=truncate(item["name"], 26), bg=theme.CARD,
                     fg=theme.TEXT, font=font(9), width=24, anchor="w").pack(side="left")

            bar = ProgressBar(row, height=8, bg=theme.CARD)
            bar.grid(row=0, column=1, sticky="ew")
            bar.set(pct(item["total"], total_expense), item["color"])

            tk.Label(row, text=self.money(item["total"]), bg=theme.CARD, fg=theme.TEXT,
                     font=font(9, "bold"), width=12, anchor="e").grid(
                row=0, column=2, padx=(12, 8))
            tk.Label(row, text=pct_text(item["total"], total_expense), bg=theme.CARD,
                     fg=theme.MUTED, font=font(9), width=5, anchor="e").grid(
                row=0, column=3)

    def _export(self):
        try:
            year = int(self.year_var.get())
        except ValueError:
            return
        path = filedialog.asksaveasfilename(
            parent=self, title="Exportar movimientos del año",
            defaultextension=".csv", filetypes=[("Archivo CSV", "*.csv")],
            initialfile=f"movimientos_{year}.csv",
        )
        if not path:
            return
        try:
            count = self.db.export_csv(path, {
                "date_from": f"{year:04d}-01-01", "date_to": f"{year:04d}-12-31",
            })
        except OSError as exc:
            self.app.toast(f"No se pudo exportar: {exc}", "error")
            return
        self.app.toast(f"{count} movimientos exportados")
