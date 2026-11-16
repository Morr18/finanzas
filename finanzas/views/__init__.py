"""Vistas de la aplicación."""
from __future__ import annotations

import tkinter as tk

from .. import theme
from ..theme import font


class BaseView(tk.Frame):
    title = ""
    subtitle = ""

    def __init__(self, app):
        super().__init__(app.content, bg=theme.BG)
        self.app = app
        self.db = app.db

    def refresh(self) -> None:  # pragma: no cover - sobreescrito
        pass

    def confirm_leave(self) -> bool:
        """Pregunta antes de salir si hay cambios sin guardar."""
        return True

    def money(self, cents: int, plus: bool = False, currency: str | None = None) -> str:
        return self.app.money(cents, plus=plus, currency=currency)

    def money_display(self, cents: int, plus: bool = False, date: str | None = None) -> str:
        return self.app.money_display(cents, plus=plus, date=date)

    def money_native(self, cents: int, currency: str | None = None,
                     date: str | None = None, plus: bool = False) -> str:
        return self.app.money_native(cents, currency=currency, date=date, plus=plus)

    def money_original(self, cents: int, currency: str | None = None,
                       plus: bool = False) -> str:
        return self.app.money_original(cents, currency=currency, plus=plus)

    def convert_display(self, cents: int, date: str | None = None) -> int:
        return self.app.convert_display(cents, date)

    def view_currency(self) -> str:
        return self.app.display_currency_code()


from .accounts import AccountsView  # noqa: E402
from .budgets import BudgetsView  # noqa: E402
from .categories import CategoriesView  # noqa: E402
from .dashboard import DashboardView  # noqa: E402
from .recurring import RecurringView  # noqa: E402
from .reports import ReportsView  # noqa: E402
from .rules import RulesView  # noqa: E402
from .settings import SettingsView  # noqa: E402
from .transactions import TransactionsView  # noqa: E402

__all__ = [
    "BaseView",
    "AccountsView",
    "BudgetsView",
    "CategoriesView",
    "DashboardView",
    "RecurringView",
    "ReportsView",
    "RulesView",
    "SettingsView",
    "TransactionsView",
]
