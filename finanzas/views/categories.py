"""Administración de categorías de ingreso y gasto."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import theme
from ..dialogs import CategoryDialog, ask_confirm
from ..theme import font
from ..utils import truncate
from ..widgets import Card, ScrollFrame
from . import BaseView


class CategoriesView(BaseView):
    title = "Categorías"
    subtitle = "Organiza tus ingresos y gastos con categorías propias"

    def __init__(self, app):
        super().__init__(app)
        self.show_archived = tk.BooleanVar(value=False)
        self._build()
        self.refresh()

    def _build(self):
        options = Card(self, padding=10)
        options.pack(fill="x")
        ttk.Checkbutton(options.inner, text="Mostrar categorías archivadas",
                        variable=self.show_archived,
                        command=self.refresh).pack(side="left")

        columns = tk.Frame(self, bg=theme.BG)
        columns.pack(fill="both", expand=True, pady=(14, 0))
        columns.columnconfigure(0, weight=1, uniform="catcol")
        columns.columnconfigure(1, weight=1, uniform="catcol")
        columns.rowconfigure(0, weight=1)

        self.income_body, self.income_count = self._build_panel(columns, "ingreso", 0)
        self.expense_body, self.expense_count = self._build_panel(columns, "egreso", 1)

    def _build_panel(self, parent, kind: str, column: int):
        card = Card(parent, padding=16)
        card.grid(row=0, column=column, sticky="nsew",
                  padx=(0, 6) if column == 0 else (6, 0))
        head = tk.Frame(card.inner, bg=theme.CARD)
        head.pack(fill="x")
        title = "Ingresos" if kind == "ingreso" else "Gastos"
        color = theme.GREEN if kind == "ingreso" else theme.RED
        dot = tk.Canvas(head, width=10, height=10, bg=theme.CARD, highlightthickness=0)
        dot.create_oval(2, 2, 9, 9, fill=color, outline="")
        dot.pack(side="left", padx=(0, 7))
        tk.Label(head, text=title, bg=theme.CARD, fg=theme.TEXT,
                 font=font(11, "bold")).pack(side="left")
        count = tk.Label(head, text="", bg=theme.CARD, fg=theme.MUTED, font=font(9))
        count.pack(side="left", padx=8)
        ttk.Button(head, text="+ Nueva", style="Secondary.TButton",
                   command=lambda k=kind: self._new(k)).pack(side="right")

        scroll = ScrollFrame(card.inner, bg=theme.CARD)
        scroll.pack(fill="both", expand=True, pady=(12, 0))
        return scroll.body, count

    # ------------------------------------------------------------ datos
    def refresh(self):
        for kind, body, count_lbl in (
            ("ingreso", self.income_body, self.income_count),
            ("egreso", self.expense_body, self.expense_count),
        ):
            for child in body.winfo_children():
                child.destroy()
            cats = self.db.categories(kind, include_archived=self.show_archived.get())
            count_lbl.configure(text=f"{len(cats)}")
            if not cats:
                tk.Label(body, text="Sin categorías. Crea la primera con «+ Nueva».",
                         bg=theme.CARD, fg=theme.SUBTLE, font=font(9),
                         wraplength=320, justify="left").pack(anchor="w", pady=10)
                continue
            for category in cats:
                self._build_row(body, category, kind)

    def _build_row(self, parent, category: dict, kind: str):
        archived = bool(category["archived"])
        row = tk.Frame(parent, bg=theme.CARD)
        row.pack(fill="x")
        row.columnconfigure(1, weight=1)

        swatch = tk.Canvas(row, width=12, height=12, bg=theme.CARD, highlightthickness=0)
        swatch.create_oval(2, 2, 11, 11, fill=category["color"], outline="")
        swatch.grid(row=0, column=0, padx=(0, 9), pady=7)

        name = tk.Frame(row, bg=theme.CARD)
        name.grid(row=0, column=1, sticky="w")
        tk.Label(name, text=truncate(category["name"], 26), bg=theme.CARD,
                 fg=theme.SUBTLE if archived else theme.TEXT,
                 font=font(9, "bold" if not archived else "normal")).pack(side="left")
        if archived:
            tk.Label(name, text="archivada", bg=theme.AMBER_SOFT, fg=theme.AMBER,
                     font=font(7, "bold"), padx=6, pady=1).pack(side="left", padx=6)

        usage = self.db.category_usage(category["id"])
        tk.Label(row, text=f"{usage} mov.", bg=theme.CARD, fg=theme.SUBTLE,
                 font=font(8), width=8, anchor="e").grid(row=0, column=2, padx=6)

        actions = tk.Frame(row, bg=theme.CARD)
        actions.grid(row=0, column=3, sticky="e")
        if archived:
            ttk.Button(actions, text="Reactivar", style="Ghost.TButton",
                       command=lambda c=category: self._toggle(c, False)).pack(side="left")
        else:
            ttk.Button(actions, text="Editar", style="Ghost.TButton",
                       command=lambda c=category: self._edit(c, kind)).pack(side="left")
        ttk.Button(actions, text="Eliminar", style="DangerLink.TButton",
                   command=lambda c=category: self._delete(c)).pack(side="left")

        tk.Frame(parent, bg=theme.BORDER, height=1).pack(fill="x")

    # ------------------------------------------------------------ acciones
    def _new(self, kind: str):
        if CategoryDialog(self, self.db, kind).run():
            self._after_change()

    def _edit(self, category: dict, kind: str):
        if CategoryDialog(self, self.db, kind, category=category).run():
            self._after_change()

    def _toggle(self, category: dict, archived: bool):
        db = self.db
        category_id = category["id"]
        db.set_category_archived(category_id, archived)
        self._after_change()
        self.app.undo_toast(
            f"Categoría {'archivada' if archived else 'reactivada'}",
            f"{'archivar' if archived else 'reactivar'} categoría",
            lambda: db.set_category_archived(category_id, not archived),
        )

    def _delete(self, category: dict):
        usage = self.db.category_usage(category["id"])
        db = self.db
        category_id = category["id"]
        if usage:
            if not ask_confirm(
                self, "Archivar categoría",
                f"«{category['name']}» tiene {usage} movimiento(s) asociado(s). "
                "Para conservar tu historial la archivaremos: dejará de aparecer al "
                "crear movimientos, pero sus datos se mantienen.",
                confirm_text="Archivar", danger=False,
            ):
                return
            db.set_category_archived(category_id, True)
            self._after_change()
            self.app.undo_toast(
                f"«{category['name']}» archivada", "archivar categoría",
                lambda: db.set_category_archived(category_id, False),
            )
        else:
            if not ask_confirm(self, "Eliminar categoría",
                               f"¿Eliminar la categoría «{category['name']}»?"):
                return
            budget = db.get_budget(category_id)
            row = dict(category)
            db.delete_category(category_id)
            self._after_change()
            self.app.undo_toast(
                f"«{category['name']}» eliminada", "eliminar categoría",
                lambda: db.restore_category(row, budget),
            )

    def _after_change(self):
        self.refresh()
        self.app.update_sidebar()
