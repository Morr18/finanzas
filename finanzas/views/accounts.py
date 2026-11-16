"""Cuentas (efectivo, banco, tarjeta, ahorro) y sus saldos."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import theme
from ..dialogs import AccountDialog, ask_confirm
from ..theme import font
from ..utils import truncate
from ..widgets import Badge, Card, ScrollFrame
from . import BaseView


class AccountsView(BaseView):
    title = "Cuentas"
    subtitle = "El saldo real de cada cuenta se calcula con sus movimientos"

    def __init__(self, app):
        super().__init__(app)
        self._build()
        self.refresh()

    def _build(self):
        top = Card(self, padding=16)
        top.pack(fill="x")
        row = tk.Frame(top.inner, bg=theme.CARD)
        row.pack(fill="x")
        left = tk.Frame(row, bg=theme.CARD)
        left.pack(side="left")
        tk.Label(left, text="BALANCE TOTAL", bg=theme.CARD, fg=theme.MUTED,
                 font=font(8, "bold")).pack(anchor="w")
        self.total_lbl = tk.Label(left, text="—", bg=theme.CARD, fg=theme.TEXT,
                                  font=font(22, "bold"))
        self.total_lbl.pack(anchor="w", pady=(2, 0))
        self.total_hint = tk.Label(left, text="", bg=theme.CARD, fg=theme.MUTED,
                                   font=font(9))
        self.total_hint.pack(anchor="w")
        ttk.Button(row, text="+ Nueva cuenta", style="Primary.TButton",
                   command=self._new).pack(side="right")

        self.rate_hint = Card(self, padding=14)
        self.rate_hint.pack_forget()

        self.scroll = ScrollFrame(self, bg=theme.BG)
        self.scroll.pack(fill="both", expand=True, pady=(14, 0))
        self.holder = self.scroll.body
        for col in range(3):
            self.holder.columnconfigure(col, weight=1, uniform="acc")

    def refresh(self):
        for child in self.holder.winfo_children():
            child.destroy()
        self._refresh_rate_hint()
        accounts = self.db.account_balances()
        total = sum(a["base_balance"] for a in accounts)
        self.total_lbl.configure(text=self.money(total), fg=self.app.color_for(total))
        if self.app.display_currency:
            hint = (f"{len(accounts)} cuenta{'s' if len(accounts) != 1 else ''} · "
                    f"convertido a {self.app.display_currency} · "
                    f"{self.app.display_rate_text()}")
        elif self.db.has_foreign_accounts():
            hint = (f"{len(accounts)} cuenta{'s' if len(accounts) != 1 else ''} · "
                    f"consolidado en {self.app.base_currency}")
        else:
            hint = (f"Suma de {len(accounts)} cuenta{'s' if len(accounts) != 1 else ''} activa"
                    f"{'s' if len(accounts) != 1 else ''}")
        self.total_hint.configure(text=hint)

        if not accounts:
            from ..widgets import EmptyState
            empty = EmptyState(self.holder, "No hay cuentas",
                               "Crea una cuenta para empezar a registrar movimientos.",
                               glyph="▦", action=self._new, action_text="Crear cuenta")
            empty.grid(row=0, column=0, columnspan=3, pady=40)
            return

        for index, account in enumerate(accounts):
            self._build_card(account, index)

    def _refresh_rate_hint(self):
        """Ofrece ver los datos convertidos si hay tasas y ninguna cuenta extranjera."""
        for child in self.rate_hint.inner.winfo_children():
            child.destroy()
        rates = self.db.fx_rates()
        if (not rates or self.db.has_foreign_accounts()
                or self.app.display_currency):
            self.rate_hint.pack_forget()
            return
        currencies = sorted({row["currency"] for row in rates})
        code = currencies[0]
        head = tk.Frame(self.rate_hint.inner, bg=theme.CARD)
        head.pack(fill="x")
        tk.Label(head, text="Ver tus datos en otra moneda", bg=theme.CARD,
                 fg=theme.TEXT, font=font(10, "bold"), anchor="w").pack(side="left")
        ttk.Button(head, text=f"Ver en {code}", style="Primary.TButton",
                   command=lambda: self.after(
                       0, lambda: self.app.set_display_currency(code)
                   )).pack(side="right")
        tk.Label(
            self.rate_hint.inner,
            text=f"Ya hay una tasa de {', '.join(currencies)} registrada. Con el "
                 "selector «Ver en» de la cabecera puedes convertir todos tus montos "
                 "sin crear cuentas nuevas ni modificar los datos guardados.",
            bg=theme.CARD, fg=theme.MUTED, font=font(9), anchor="w",
            wraplength=900, justify="left",
        ).pack(fill="x", pady=(4, 0))
        self.rate_hint.pack(fill="x", pady=(14, 0), before=self.scroll)

    def _new_currency(self, code: str):
        if AccountDialog(self, self.db, default_currency=code,
                         default_name=f"Cuenta {code}").run():
            self._after_change()

    def _build_card(self, account: dict, index: int):
        row, col = divmod(index, 3)
        card = Card(self.holder, padding=16)
        card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        inner = card.inner

        head = tk.Frame(inner, bg=theme.CARD)
        head.pack(fill="x")
        label, fg, bg = theme.ACCOUNT_KINDS.get(
            account["kind"], theme.ACCOUNT_KINDS["efectivo"]
        )
        tk.Label(head, text=truncate(account["name"], 20), bg=theme.CARD, fg=theme.TEXT,
                 font=font(11, "bold"), anchor="w").pack(side="left")
        Badge(head, label, fg=fg, bg=bg).pack(side="right")

        balance = account["balance"]
        currency = account.get("currency") or ""
        tk.Label(inner, text=self.money_native(balance, currency), bg=theme.CARD,
                 fg=self.app.color_for(balance), font=font(18, "bold"),
                 anchor="w").pack(fill="x", pady=(12, 0))
        initial_text = self.money_original(account['initial_balance'], currency)
        if self.app.display_currency:
            native_code = currency or self.app.base_currency
            tk.Label(
                inner,
                text=f"Saldo inicial {initial_text} · cuenta en {native_code}",
                bg=theme.CARD, fg=theme.MUTED, font=font(8), anchor="w",
            ).pack(fill="x")
        elif currency:
            conversion = self.money_display(account["base_balance"])
            tk.Label(
                inner,
                text=f"Saldo inicial {initial_text} · Equivalente: {conversion} "
                     f"{self.app.base_currency}",
                bg=theme.CARD, fg=theme.MUTED, font=font(8), anchor="w",
            ).pack(fill="x")
        else:
            tk.Label(inner, text=f"Saldo inicial {initial_text}",
                     bg=theme.CARD, fg=theme.MUTED, font=font(8), anchor="w").pack(fill="x")
        usage = self.db.account_usage(account["id"])
        tk.Label(inner, text=f"{usage} movimiento{'s' if usage != 1 else ''}",
                 bg=theme.CARD, fg=theme.SUBTLE, font=font(8), anchor="w").pack(
            fill="x", pady=(2, 0))

        actions = tk.Frame(inner, bg=theme.CARD)
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Editar", style="Secondary.TButton",
                   command=lambda a=account: self._edit(a)).pack(side="left")
        ttk.Button(actions, text="Eliminar", style="DangerLink.TButton",
                   command=lambda a=account: self._delete(a)).pack(side="left", padx=4)

    # ------------------------------------------------------------ acciones
    def _new(self):
        if AccountDialog(self, self.db).run():
            self._after_change()

    def _edit(self, account: dict):
        if AccountDialog(self, self.db, account=account).run():
            self._after_change()

    def _delete(self, account: dict):
        usage = self.db.account_usage(account["id"])
        if usage:
            self.app.toast(
                f"«{account['name']}» tiene {usage} movimientos y no se puede eliminar.",
                "error",
            )
            return
        if not ask_confirm(self, "Eliminar cuenta",
                           f"¿Eliminar la cuenta «{account['name']}»? "
                           "Podrás recuperarla con «Deshacer»."):
            return
        db = self.db
        row = dict(account)
        db.delete_account(account["id"])
        self._after_change()
        self.app.undo_toast("Cuenta eliminada", "eliminar cuenta",
                            lambda: db.restore_account(row))

    def _after_change(self):
        self.refresh()
        self.app.update_sidebar()
