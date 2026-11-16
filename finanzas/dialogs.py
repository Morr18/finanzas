"""Diálogos modales de la aplicación."""
from __future__ import annotations

import datetime as dt
import re
import sqlite3
import tkinter as tk
from tkinter import ttk

from . import theme
from .theme import font
from .utils import (
    DIAS_SEMANA, FREQUENCY_LABELS, fmt_date, money_input, parse_amount,
    parse_date, today_iso,
)
from .widgets import form_label

CANCEL = "Cancelar"


def _host_app(widget):
    """Busca la App subiendo por la jerarquía de widgets."""
    node = widget
    while node is not None:
        if hasattr(node, "push_undo") and hasattr(node, "toast"):
            return node
        node = getattr(node, "master", None)
    return None


class BaseDialog(tk.Toplevel):
    _open: list["BaseDialog"] = []

    def __init__(self, parent, title: str, width: int = 560):
        super().__init__(parent)
        BaseDialog._open.append(self)
        self.withdraw()
        self.title(title)
        self.configure(bg=theme.CARD)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.result = None
        self._width = width
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _e: self._cancel())

        header = tk.Frame(self, bg=theme.CARD)
        header.pack(fill="x", padx=24, pady=(18, 4))
        tk.Label(header, text=title, bg=theme.CARD, fg=theme.TEXT,
                 font=font(14, "bold"), anchor="w").pack(side="left")
        ttk.Button(header, text="×", style="Ghost.TButton", width=3,
                   command=self._cancel).pack(side="right")

        self.body = tk.Frame(self, bg=theme.CARD)
        self.body.pack(fill="both", expand=True, padx=24, pady=(10, 0))

        self.footer = tk.Frame(self, bg=theme.CARD)
        self.footer.pack(fill="x", padx=24, pady=(16, 20))

        self.error_lbl = tk.Label(self.footer, text="", bg=theme.CARD, fg=theme.RED,
                                  font=font(9), anchor="w", justify="left",
                                  wraplength=width - 60)
        self.error_lbl.pack(fill="x", pady=(0, 6))

    def show_error(self, message: str):
        self.error_lbl.configure(text=message)

    def destroy(self):
        try:
            BaseDialog._open.remove(self)
        except ValueError:
            pass
        super().destroy()

    @classmethod
    def has_open(cls) -> bool:
        cls._open = [dlg for dlg in cls._open if _still_open(dlg)]
        return bool(cls._open)

    @classmethod
    def focus_open(cls) -> None:
        for dialog in reversed(cls._open):
            if _still_open(dialog):
                try:
                    dialog.lift()
                    dialog.focus_set()
                except tk.TclError:
                    pass
                return

    def _finish(self, result):
        self.result = result
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    def run(self):
        self.update_idletasks()
        width = max(self._width, self.winfo_reqwidth())
        height = self.winfo_reqheight()
        parent = self.master
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 3)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()
        self.grab_set()
        self.focus_set()
        self.wait_window()
        return self.result


def _still_open(widget) -> bool:
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        return False


def ask_confirm(parent, title: str, message: str, confirm_text: str = "Eliminar",
                danger: bool = True) -> bool:
    dialog = BaseDialog(parent, title, width=470)
    tk.Label(dialog.body, text=message, bg=theme.CARD, fg=theme.TEXT, font=font(10),
             justify="left", anchor="w", wraplength=410).pack(fill="x", pady=(4, 10))
    ttk.Button(
        dialog.footer, text=confirm_text,
        style="DangerSolid.TButton" if danger else "Primary.TButton",
        command=lambda: dialog._finish(True),
    ).pack(side="right")
    ttk.Button(dialog.footer, text=CANCEL, style="Secondary.TButton",
               command=dialog._cancel).pack(side="right", padx=(0, 8))
    return bool(dialog.run())


def _parse_initial(text: str) -> int:
    raw = (text or "").strip().replace("$", "").replace(" ", "")
    if not raw:
        return 0
    negative = raw.startswith("-")
    if negative:
        raw = raw[1:]
    if re.fullmatch(r"0([.,]0+)?", raw or "0"):
        return 0
    value = parse_amount(raw)
    return -value if negative else value


def color_palette(parent, initial: str, bg: str | None = None):
    """Devuelve (frame, estado) donde estado['color'] es el color elegido."""
    bg = theme.CARD if bg is None else bg
    holder = tk.Frame(parent, bg=bg)
    state = {"color": initial if initial in theme.CATEGORY_COLORS else theme.CATEGORY_COLORS[0]}
    swatches: dict[str, tk.Frame] = {}

    def select(color: str):
        state["color"] = color
        for value, widget in swatches.items():
            widget.configure(highlightbackground=theme.TEXT if value == color else bg)

    for index, color in enumerate(theme.CATEGORY_COLORS):
        row, col = divmod(index, 7)
        swatch = tk.Frame(holder, width=24, height=24, bg=color, cursor="hand2",
                          highlightthickness=2, highlightbackground=bg)
        swatch.grid(row=row, column=col, padx=3, pady=3)
        swatch.pack_propagate(False)
        swatch.bind("<Button-1>", lambda _e, c=color: select(c))
        swatches[color] = swatch
    select(state["color"])
    return holder, state


class TransactionDialog(BaseDialog):
    def __init__(self, parent, db, tx: dict | None = None, on_saved=None,
                 default_kind: str = "egreso"):
        super().__init__(parent, "Editar movimiento" if tx else "Nuevo movimiento", 620)
        self.db = db
        self.tx = tx
        self.on_saved = on_saved
        self.host_app = _host_app(parent)
        self.accounts = db.accounts()
        self.categories = db.categories(include_archived=True)
        self._dirty = False

        if not self.accounts:
            tk.Label(self.body, text="Primero crea una cuenta en la sección Cuentas.",
                     bg=theme.CARD, fg=theme.RED, font=font(10)).pack(pady=20)
            ttk.Button(self.footer, text="Cerrar", style="Secondary.TButton",
                       command=self._cancel).pack(side="right")
            return

        self.kind_var = tk.StringVar(value=(tx["kind"] if tx else default_kind))
        self.amount_var = tk.StringVar()
        self.date_var = tk.StringVar(value=fmt_date(tx["date"]) if tx else fmt_date(today_iso()))
        self.category_var = tk.StringVar()
        self.account_var = tk.StringVar()
        self.origin_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.desc_var = tk.StringVar()
        self.received_var = tk.StringVar()
        self.apply_rules_var = tk.BooleanVar(value=True)
        self.rule_hint: tk.Label | None = None
        self._last_rule_id = None
        self._initial_category = tx.get("category_id") if tx else None
        self._initial_account = tx.get("account_id") if tx else None
        self._initial_dest = tx.get("transfer_account_id") if tx else None

        self._build()
        self._prefill(tx)

    # ------------------------------------------------------------ interfaz
    def _build(self):
        form = tk.Frame(self.body, bg=theme.CARD)
        form.pack(fill="x")
        form.columnconfigure(0, weight=1, uniform="col")
        form.columnconfigure(1, weight=1, uniform="col")

        # tipo
        kind_box = tk.Frame(form, bg=theme.CARD)
        kind_box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        form_label(kind_box, "TIPO DE MOVIMIENTO").pack(fill="x", pady=(0, 5))
        buttons = tk.Frame(kind_box, bg=theme.CARD)
        buttons.pack(fill="x")
        self.kind_buttons = {}
        for kind, label in (("egreso", "Egreso"), ("ingreso", "Ingreso"),
                            ("transferencia", "Transferencia")):
            btn = ttk.Button(buttons, text=label, style="Secondary.TButton",
                             command=lambda k=kind: self._set_kind(k))
            btn.pack(side="left", padx=(0, 6))
            self.kind_buttons[kind] = btn

        # monto y fecha
        amount_holder = tk.Frame(form, bg=theme.CARD)
        amount_holder.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
        self.amount_label = form_label(amount_holder, "MONTO")
        self.amount_label.pack(fill="x", pady=(0, 5))
        ttk.Entry(amount_holder, textvariable=self.amount_var, style="Big.TEntry",
                  justify="right").pack(fill="x")

        date_holder = tk.Frame(form, bg=theme.CARD)
        date_holder.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 12))
        form_label(date_holder, "FECHA (dd/mm/aaaa)").pack(fill="x", pady=(0, 5))
        date_row = tk.Frame(date_holder, bg=theme.CARD)
        date_row.pack(fill="x")
        ttk.Entry(date_row, textvariable=self.date_var).pack(side="left", fill="x", expand=True)
        ttk.Button(date_row, text="Hoy", style="Ghost.TButton",
                   command=lambda: self.date_var.set(fmt_date(today_iso()))).pack(
            side="left", padx=(4, 0))

        # fila categoría / cuenta (normal)
        self.normal_row = tk.Frame(form, bg=theme.CARD)
        self.normal_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.normal_row.columnconfigure(0, weight=1, uniform="col2")
        self.normal_row.columnconfigure(1, weight=1, uniform="col2")
        cat_holder = tk.Frame(self.normal_row, bg=theme.CARD)
        cat_holder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        form_label(cat_holder, "CATEGORÍA").pack(fill="x", pady=(0, 5))
        self.category_combo = ttk.Combobox(cat_holder, textvariable=self.category_var,
                                           state="readonly")
        self.category_combo.pack(fill="x")
        self.category_combo.bind("<<ComboboxSelected>>", self._on_category_change)
        acc_holder = tk.Frame(self.normal_row, bg=theme.CARD)
        acc_holder.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        form_label(acc_holder, "CUENTA").pack(fill="x", pady=(0, 5))
        self.account_combo = ttk.Combobox(
            acc_holder, textvariable=self.account_var, state="readonly",
            values=[a["name"] for a in self.accounts],
        )
        self.account_combo.pack(fill="x")
        self.account_combo.bind("<<ComboboxSelected>>",
                                lambda _e: self._update_currency_hint())

        # fila cuentas (transferencia)
        self.transfer_row = tk.Frame(form, bg=theme.CARD)
        self.transfer_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.transfer_row.columnconfigure(0, weight=1, uniform="col3")
        self.transfer_row.columnconfigure(1, weight=1, uniform="col3")
        origin_holder = tk.Frame(self.transfer_row, bg=theme.CARD)
        origin_holder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        form_label(origin_holder, "CUENTA DE ORIGEN").pack(fill="x", pady=(0, 5))
        self.origin_combo = ttk.Combobox(
            origin_holder, textvariable=self.origin_var, state="readonly",
            values=[a["name"] for a in self.accounts],
        )
        self.origin_combo.pack(fill="x")
        dest_holder = tk.Frame(self.transfer_row, bg=theme.CARD)
        dest_holder.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        form_label(dest_holder, "CUENTA DE DESTINO").pack(fill="x", pady=(0, 5))
        self.dest_combo = ttk.Combobox(
            dest_holder, textvariable=self.dest_var, state="readonly",
            values=[a["name"] for a in self.accounts],
        )
        self.dest_combo.pack(fill="x")
        self.origin_combo.bind("<<ComboboxSelected>>",
                               lambda _e: self._update_currency_hint())
        self.dest_combo.bind("<<ComboboxSelected>>",
                             lambda _e: self._update_currency_hint())

        self.received_holder = tk.Frame(self.transfer_row, bg=theme.CARD)
        self.received_holder.grid(row=1, column=0, columnspan=2, sticky="ew",
                                  pady=(10, 0))
        form_label(self.received_holder,
                   "MONTO RECIBIDO EN LA CUENTA DE DESTINO (OPCIONAL)").pack(
            fill="x", pady=(0, 5))
        ttk.Entry(self.received_holder, textvariable=self.received_var).pack(fill="x")
        self.currency_hint = tk.Label(
            self.received_holder,
            text="Si las cuentas usan monedas distintas y lo dejas vacío, "
                 "se calcula con el tipo de cambio.",
            bg=theme.CARD, fg=theme.MUTED, font=font(8), anchor="w",
            wraplength=540, justify="left",
        )
        self.currency_hint.pack(fill="x", pady=(4, 0))

        # descripción
        desc_holder = tk.Frame(form, bg=theme.CARD)
        desc_holder.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        form_label(desc_holder, "DESCRIPCIÓN (OPCIONAL)").pack(fill="x", pady=(0, 5))
        desc_entry = ttk.Entry(desc_holder, textvariable=self.desc_var)
        desc_entry.pack(fill="x")
        self.desc_var.trace_add("write", lambda *_a: self._update_rule_hint())

        # notas
        notes_holder = tk.Frame(form, bg=theme.CARD)
        notes_holder.grid(row=4, column=0, columnspan=2, sticky="ew")
        form_label(notes_holder, "NOTAS (OPCIONAL)").pack(fill="x", pady=(0, 5))
        self.notes_text = tk.Text(
            notes_holder, height=3, bg=theme.CARD_SOFT, fg=theme.TEXT, font=font(10),
            relief="flat", highlightthickness=1, highlightbackground=theme.BORDER_STRONG,
            highlightcolor=theme.PRIMARY, padx=8, pady=6, wrap="word",
        )
        self.notes_text.pack(fill="x")
        self.notes_text.bind("<KeyRelease>", lambda _e: self._update_rule_hint())

        # reglas automáticas (solo al crear)
        self.rule_box = tk.Frame(form, bg=theme.CARD)
        self.rule_box.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        if not self.tx:
            ttk.Checkbutton(
                self.rule_box, text="Aplicar reglas automáticas",
                variable=self.apply_rules_var, command=self._update_rule_hint,
            ).pack(anchor="w")
            self.rule_hint = tk.Label(
                self.rule_box, text="", bg=theme.CARD, fg=theme.SUBTLE,
                font=font(8), anchor="w", justify="left", wraplength=540,
            )
            self.rule_hint.pack(fill="x", pady=(3, 0))
        else:
            self.rule_box.grid_remove()

        # pie
        if self.tx:
            ttk.Button(self.footer, text="Eliminar", style="Danger.TButton",
                       command=self._delete).pack(side="left")
        ttk.Button(self.footer, text="Guardar movimiento", style="Primary.TButton",
                   command=self._save).pack(side="right")
        ttk.Button(self.footer, text=CANCEL, style="Secondary.TButton",
                   command=self._cancel).pack(side="right", padx=(0, 8))

        self._set_kind(self.kind_var.get(), initial=True)

    def _prefill(self, tx: dict | None):
        if not tx:
            self.account_var.set(self.accounts[0]["name"])
            self.origin_var.set(self.accounts[0]["name"])
            self.dest_var.set(self.accounts[1]["name"] if len(self.accounts) > 1 else "")
            self._update_currency_hint()
            return
        style = getattr(self.host_app, "number_format", "en")
        self.amount_var.set(money_input(tx["amount"], style))
        self.desc_var.set(tx.get("description") or "")
        if tx.get("notes"):
            self.notes_text.insert("1.0", tx["notes"])
        if tx.get("account_name"):
            self.account_var.set(tx["account_name"])
            self.origin_var.set(tx["account_name"])
        if tx.get("transfer_account_name"):
            self.dest_var.set(tx["transfer_account_name"])
        if tx.get("transfer_amount"):
            self.received_var.set(money_input(tx["transfer_amount"], style))
        self._refresh_category_values()
        if tx.get("category_name"):
            self.category_var.set(tx["category_name"])
        self._update_currency_hint()

    # ------------------------------------------------------------ reglas y monedas
    def _account_for_var(self, var: tk.StringVar) -> dict | None:
        name = var.get()
        return next((a for a in self.accounts if a["name"] == name), None)

    def _update_currency_hint(self):
        if not hasattr(self, "amount_label"):
            return
        var = self.origin_var if self.kind_var.get() == "transferencia" else self.account_var
        account = self._account_for_var(var)
        base = getattr(self.host_app, "base_currency", "") or ""
        code = (account or {}).get("currency") or base
        self.amount_label.configure(text=f"MONTO ({code})" if code else "MONTO")
        if self.kind_var.get() == "transferencia" and hasattr(self, "currency_hint"):
            source = self._account_for_var(self.origin_var)
            target = self._account_for_var(self.dest_var)
            source_code = (source or {}).get("currency") or base
            target_code = (target or {}).get("currency") or base
            if source and target and source_code != target_code:
                self.currency_hint.configure(
                    text=f"De {source_code} a {target_code}. Si dejas el monto recibido "
                         "vacío, se calcula con el tipo de cambio de la fecha.",
                    fg=theme.AMBER,
                )
            else:
                self.currency_hint.configure(
                    text="Si las cuentas usan monedas distintas y lo dejas vacío, "
                         "se calcula con el tipo de cambio.",
                    fg=theme.MUTED,
                )

    def _update_rule_hint(self):
        if not self.rule_hint:
            return
        if self.kind_var.get() == "transferencia":
            self.rule_hint.configure(text="")
            return
        if not self.apply_rules_var.get():
            self.rule_hint.configure(
                text="Las reglas automáticas no se aplicarán a este movimiento.",
                fg=theme.SUBTLE,
            )
            return
        description = self.desc_var.get().strip()
        notes = self.notes_text.get("1.0", "end").strip()
        rule = self.db.match_rule(description, notes, self.kind_var.get())
        if not rule:
            self.rule_hint.configure(text="", fg=theme.SUBTLE)
            self._last_rule_id = None
            return
        if rule["id"] != self._last_rule_id:
            if rule.get("category_id"):
                category = self.db.get_category(rule["category_id"])
                if category:
                    self.category_var.set(category["name"])
            if rule.get("account_id"):
                account = self.db.get_account(rule["account_id"])
                if account:
                    self.account_var.set(account["name"])
            self._last_rule_id = rule["id"]
            self._update_currency_hint()
        detail = []
        if rule.get("category_name"):
            detail.append(rule["category_name"])
        if rule.get("account_name"):
            detail.append(rule["account_name"])
        suffix = " → " + " · ".join(detail) if detail else ""
        self.rule_hint.configure(
            text=f"Regla «{rule['match_text']}»{suffix}. Se aplicará al guardar.",
            fg=theme.PRIMARY_DARK,
        )

    # ------------------------------------------------------------ lógica
    def _set_kind(self, kind: str, initial: bool = False):
        self.kind_var.set(kind)
        for key, btn in self.kind_buttons.items():
            btn.configure(style="Primary.TButton" if key == kind else "Secondary.TButton")
        self._refresh_category_values()
        if kind == "transferencia":
            self.normal_row.grid_remove()
            self.transfer_row.grid()
            if hasattr(self, "rule_box"):
                self.rule_box.grid_remove()
            if not initial:
                if self.account_var.get():
                    self.origin_var.set(self.account_var.get())
                if not self.dest_var.get() or self.dest_var.get() == self.origin_var.get():
                    others = [a["name"] for a in self.accounts if a["name"] != self.origin_var.get()]
                    if others:
                        self.dest_var.set(others[0])
        else:
            self.transfer_row.grid_remove()
            self.normal_row.grid()
            if hasattr(self, "rule_box") and not self.tx:
                self.rule_box.grid()
            self._refresh_category_values()
        self._update_currency_hint()
        self._update_rule_hint()

    def _refresh_category_values(self):
        kind = "ingreso" if self.kind_var.get() == "ingreso" else "egreso"
        options = [c for c in self.categories if c["kind"] == kind]
        values = ["Sin categoría"] + [c["name"] for c in options]
        self.category_combo.configure(values=values)
        self._category_map = {c["name"]: c["id"] for c in options}
        if self.category_var.get() not in values:
            if self._initial_category:
                match = next((c for c in options if c["id"] == self._initial_category), None)
                self.category_var.set(match["name"] if match else "Sin categoría")
            else:
                self.category_var.set("Sin categoría")

    def _on_category_change(self, _event=None):
        pass

    def _selected_account_id(self, var: tk.StringVar) -> int | None:
        name = var.get()
        return next((a["id"] for a in self.accounts if a["name"] == name), None)

    def _save(self):
        try:
            amount = parse_amount(self.amount_var.get())
            date = parse_date(self.date_var.get()).isoformat()
            kind = self.kind_var.get()
            notes = self.notes_text.get("1.0", "end").strip()
            description = self.desc_var.get().strip()
            received = None

            if kind == "transferencia":
                source = self._selected_account_id(self.origin_var)
                dest = self._selected_account_id(self.dest_var)
                if not source or not dest:
                    raise ValueError("Selecciona la cuenta de origen y la de destino.")
                if source == dest:
                    raise ValueError("Las cuentas de origen y destino deben ser distintas.")
                category_id = None
                account_id, transfer_id = source, dest
                raw_received = self.received_var.get().strip()
                if raw_received:
                    received = parse_amount(raw_received)
                if not description:
                    description = "Transferencia entre cuentas"
            else:
                account_id = self._selected_account_id(self.account_var)
                if not account_id:
                    raise ValueError("Selecciona una cuenta.")
                category_id = self._category_map.get(self.category_var.get())
                transfer_id = None
                if not description and category_id:
                    category = next((c for c in self.categories if c["id"] == category_id), None)
                    description = category["name"] if category else ""

            db = self.db
            if self.tx:
                before = {key: self.tx.get(key) for key in (
                    "date", "kind", "amount", "transfer_amount", "category_id",
                    "account_id", "transfer_account_id", "description", "notes",
                )}
                tx_id = self.tx["id"]
                db.update_transaction(
                    tx_id, date, kind, amount, category_id, account_id,
                    transfer_id, description, notes, transfer_amount=received,
                )

                def undo_edit():
                    db.update_transaction(
                        tx_id, before["date"], before["kind"], before["amount"],
                        before["category_id"], before["account_id"],
                        before["transfer_account_id"], before["description"],
                        before["notes"], transfer_amount=before["transfer_amount"],
                    )

                if self.host_app is not None:
                    self.host_app.undo_toast("Movimiento actualizado",
                                             "editar movimiento", undo_edit)
            else:
                apply_rules = self.apply_rules_var.get()
                applied = (db.match_rule(description, notes, kind)
                           if apply_rules else None)
                db.add_transaction(
                    date, kind, amount, category_id, account_id, transfer_id,
                    description, notes, transfer_amount=received,
                    apply_rules=apply_rules,
                )
                if self.host_app is not None:
                    if applied:
                        self.host_app.toast(
                            f"Movimiento registrado · regla «{applied['match_text']}» aplicada"
                        )
                    else:
                        self.host_app.toast("Movimiento registrado")
        except (ValueError, sqlite3.Error) as exc:
            self.show_error(str(exc))
            return

        if self.on_saved:
            self.on_saved()
        self._finish(True)

    def _delete(self):
        if not self.tx:
            return
        if not ask_confirm(self, "Eliminar movimiento",
                           "¿Seguro que quieres eliminar este movimiento? "
                           "Podrás recuperarlo con «Deshacer»."):
            return
        db = self.db
        tx = dict(self.tx)
        db.delete_transaction(tx["id"])
        if self.host_app is not None:
            self.host_app.undo_toast(
                "Movimiento eliminado", "eliminar movimiento",
                lambda: db.restore_transaction(tx),
            )
        if self.on_saved:
            self.on_saved()
        self._finish("deleted")


class CategoryDialog(BaseDialog):
    def __init__(self, parent, db, kind: str, category: dict | None = None, on_saved=None):
        super().__init__(parent, "Editar categoría" if category else "Nueva categoría", 480)
        self.db = db
        self.kind = kind
        self.category = category
        self.on_saved = on_saved

        head = tk.Frame(self.body, bg=theme.CARD)
        head.pack(fill="x", pady=(0, 12))
        label = "Ingreso" if kind == "ingreso" else "Gasto"
        fg = theme.GREEN if kind == "ingreso" else theme.RED
        bg = theme.GREEN_SOFT if kind == "ingreso" else theme.RED_SOFT
        tk.Label(head, text=f"Categoría de {label.lower()}", bg=bg, fg=fg,
                 font=font(9, "bold"), padx=10, pady=3).pack(side="left")

        form_label(self.body, "NOMBRE").pack(fill="x", pady=(4, 5))
        self.name_var = tk.StringVar(value=category["name"] if category else "")
        entry = ttk.Entry(self.body, textvariable=self.name_var)
        entry.pack(fill="x")
        entry.focus_set()

        form_label(self.body, "COLOR").pack(fill="x", pady=(14, 5))
        palette, self.palette_state = color_palette(
            self.body, category["color"] if category else theme.CATEGORY_COLORS[0]
        )
        palette.pack(anchor="w")

        ttk.Button(self.footer, text="Guardar", style="Primary.TButton",
                   command=self._save).pack(side="right")
        ttk.Button(self.footer, text=CANCEL, style="Secondary.TButton",
                   command=self._cancel).pack(side="right", padx=(0, 8))
        self.bind("<Return>", lambda _e: self._save())

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            self.show_error("Escribe un nombre para la categoría.")
            return
        if len(name) > 40:
            self.show_error("El nombre no puede superar los 40 caracteres.")
            return
        try:
            if self.category:
                self.db.update_category(self.category["id"], name, self.kind,
                                        self.palette_state["color"])
            else:
                self.db.add_category(name, self.kind, self.palette_state["color"])
        except sqlite3.IntegrityError:
            self.show_error("Ya existe una categoría con ese nombre.")
            return
        if self.on_saved:
            self.on_saved()
        self._finish(True)


class AccountDialog(BaseDialog):
    def __init__(self, parent, db, account: dict | None = None, on_saved=None,
                 default_currency: str = "", default_name: str = ""):
        super().__init__(parent, "Editar cuenta" if account else "Nueva cuenta", 480)
        self.db = db
        self.account = account
        self.on_saved = on_saved

        form_label(self.body, "NOMBRE").pack(fill="x", pady=(4, 5))
        self.name_var = tk.StringVar(
            value=account["name"] if account else default_name
        )
        entry = ttk.Entry(self.body, textvariable=self.name_var)
        entry.pack(fill="x")
        entry.focus_set()

        form_label(self.body, "TIPO DE CUENTA").pack(fill="x", pady=(12, 5))
        self._kind_by_label = {v[0]: k for k, v in theme.ACCOUNT_KINDS.items()}
        current_kind = account["kind"] if account else "efectivo"
        self.kind_label_var = tk.StringVar(
            value=theme.ACCOUNT_KINDS.get(current_kind, theme.ACCOUNT_KINDS["efectivo"])[0]
        )
        ttk.Combobox(self.body, textvariable=self.kind_label_var, state="readonly",
                     values=list(self._kind_by_label.keys())).pack(fill="x")

        form_label(self.body, "SALDO INICIAL").pack(fill="x", pady=(12, 5))
        style = getattr(_host_app(parent), "number_format", "en")
        self.initial_var = tk.StringVar(
            value=money_input(account["initial_balance"], style) if account
            else money_input(0, style) or "0"
        )
        ttk.Entry(self.body, textvariable=self.initial_var).pack(fill="x")
        tk.Label(self.body, text="Puede ser negativo (por ejemplo, deuda de una tarjeta).",
                 bg=theme.CARD, fg=theme.MUTED, font=font(8), anchor="w").pack(
            fill="x", pady=(4, 0))

        form_label(self.body, "MONEDA (OPCIONAL)").pack(fill="x", pady=(12, 5))
        base_code = self.db.base_currency()
        self.currency_var = tk.StringVar(
            value=(account.get("currency") or "") if account else default_currency
        )
        self.currency_entry = ttk.Entry(self.body, textvariable=self.currency_var, width=10)
        self.currency_entry.pack(fill="x")
        usage = self.db.account_usage(account["id"]) if account else 0
        if usage:
            self.currency_entry.configure(state="disabled")
        tk.Label(
            self.body,
            text=f"Código ISO de 3 a 5 letras (USD, EUR…). Vacío = moneda base ({base_code})."
                 + (" No se puede cambiar porque la cuenta ya tiene movimientos."
                    if usage else ""),
            bg=theme.CARD, fg=theme.MUTED, font=font(8), anchor="w",
            wraplength=420, justify="left",
        ).pack(fill="x", pady=(4, 0))

        form_label(self.body, "COLOR").pack(fill="x", pady=(14, 5))
        palette, self.palette_state = color_palette(
            self.body, account["color"] if account else theme.CATEGORY_COLORS[9]
        )
        palette.pack(anchor="w")

        ttk.Button(self.footer, text="Guardar", style="Primary.TButton",
                   command=self._save).pack(side="right")
        ttk.Button(self.footer, text=CANCEL, style="Secondary.TButton",
                   command=self._cancel).pack(side="right", padx=(0, 8))
        self.bind("<Return>", lambda _e: self._save())

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            self.show_error("Escribe un nombre para la cuenta.")
            return
        if len(name) > 40:
            self.show_error("El nombre no puede superar los 40 caracteres.")
            return
        try:
            initial = _parse_initial(self.initial_var.get())
        except ValueError:
            self.show_error("El saldo inicial no es válido.")
            return
        kind = self._kind_by_label.get(self.kind_label_var.get(), "efectivo")
        code = self.currency_var.get().strip().upper()
        if self.account and self.db.account_usage(self.account["id"]) \
                and code != (self.account.get("currency") or ""):
            self.show_error("No se puede cambiar la moneda de una cuenta con movimientos.")
            return
        try:
            if self.account:
                self.db.update_account(self.account["id"], name, kind, initial,
                                       self.palette_state["color"], currency=code)
            else:
                self.db.add_account(name, kind, initial, self.palette_state["color"],
                                    currency=code)
        except ValueError as exc:
            self.show_error(str(exc))
            return
        except sqlite3.IntegrityError:
            self.show_error("Ya existe una cuenta con ese nombre.")
            return
        if self.on_saved:
            self.on_saved()
        self._finish(True)


class RecurringDialog(BaseDialog):
    """Alta y edición de movimientos recurrentes."""

    def __init__(self, parent, db, rule: dict | None = None, on_saved=None):
        super().__init__(parent, "Editar recurrente" if rule else "Nuevo movimiento recurrente", 650)
        self.db = db
        self.rule = rule
        self.on_saved = on_saved
        self.host_app = _host_app(parent)
        self.accounts = db.accounts()
        self.categories = db.categories(include_archived=True)
        self._category_map: dict[str, int] = {}
        self._initial_category = rule.get("category_id") if rule else None

        if not self.accounts:
            tk.Label(self.body, text="Primero crea una cuenta en la sección Cuentas.",
                     bg=theme.CARD, fg=theme.RED, font=font(10)).pack(pady=20)
            ttk.Button(self.footer, text="Cerrar", style="Secondary.TButton",
                       command=self._cancel).pack(side="right")
            return

        self.kind_var = tk.StringVar(value=rule["kind"] if rule else "egreso")
        self.amount_var = tk.StringVar()
        self.start_var = tk.StringVar(
            value=fmt_date(rule["start_date"]) if rule else fmt_date(today_iso())
        )
        self.category_var = tk.StringVar()
        self.account_var = tk.StringVar()
        self.origin_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.desc_var = tk.StringVar(value=rule.get("description", "") if rule else "")
        self.freq_var = tk.StringVar(value="Mensual")
        self.day_var = tk.StringVar(value="1")
        self.weekday_var = tk.StringVar(value=DIAS_SEMANA[0])
        self.month_var = tk.StringVar(value="Enero")
        self.active_var = tk.BooleanVar(value=bool(rule.get("active", 1)) if rule else True)

        self._build()
        self._prefill(rule)
        self._on_frequency_change()

    def _build(self):
        form = tk.Frame(self.body, bg=theme.CARD)
        form.pack(fill="x")
        form.columnconfigure(0, weight=1, uniform="rcol")
        form.columnconfigure(1, weight=1, uniform="rcol")

        kind_box = tk.Frame(form, bg=theme.CARD)
        kind_box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        form_label(kind_box, "TIPO DE MOVIMIENTO").pack(fill="x", pady=(0, 5))
        buttons = tk.Frame(kind_box, bg=theme.CARD)
        buttons.pack(fill="x")
        self.kind_buttons = {}
        for kind, label in (("egreso", "Egreso"), ("ingreso", "Ingreso"),
                            ("transferencia", "Transferencia")):
            btn = ttk.Button(buttons, text=label, style="Secondary.TButton",
                             command=lambda k=kind: self._set_kind(k))
            btn.pack(side="left", padx=(0, 6))
            self.kind_buttons[kind] = btn

        amount_holder = tk.Frame(form, bg=theme.CARD)
        amount_holder.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
        self.amount_label = form_label(amount_holder, "MONTO")
        self.amount_label.pack(fill="x", pady=(0, 5))
        ttk.Entry(amount_holder, textvariable=self.amount_var, style="Big.TEntry",
                  justify="right").pack(fill="x")

        start_holder = tk.Frame(form, bg=theme.CARD)
        start_holder.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 12))
        form_label(start_holder, "FECHA DE INICIO (dd/mm/aaaa)").pack(fill="x", pady=(0, 5))
        ttk.Entry(start_holder, textvariable=self.start_var).pack(fill="x")

        freq_holder = tk.Frame(form, bg=theme.CARD)
        freq_holder.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        form_label(freq_holder, "FRECUENCIA").pack(fill="x", pady=(0, 5))
        freq_row = tk.Frame(freq_holder, bg=theme.CARD)
        freq_row.pack(fill="x")
        self.freq_combo = ttk.Combobox(
            freq_row, textvariable=self.freq_var, state="readonly", width=14,
            values=list(FREQUENCY_LABELS.values()),
        )
        self.freq_combo.pack(side="left")
        self.freq_combo.bind("<<ComboboxSelected>>",
                             lambda _e: self._on_frequency_change())
        self.freq_hint = tk.Label(freq_row, text="", bg=theme.CARD, fg=theme.MUTED,
                                  font=font(8), anchor="w")
        self.freq_hint.pack(side="left", padx=(10, 0))

        self.detail_row = tk.Frame(form, bg=theme.CARD)
        self.detail_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        for col in range(3):
            self.detail_row.columnconfigure(col, weight=1, uniform="rdet")

        self.day_holder = tk.Frame(self.detail_row, bg=theme.CARD)
        self.day_holder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        form_label(self.day_holder, "DÍA DEL MES (1-31)").pack(fill="x", pady=(0, 5))
        ttk.Spinbox(self.day_holder, from_=1, to=31, textvariable=self.day_var).pack(fill="x")

        self.week_holder = tk.Frame(self.detail_row, bg=theme.CARD)
        self.week_holder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        form_label(self.week_holder, "DÍA DE LA SEMANA").pack(fill="x", pady=(0, 5))
        ttk.Combobox(self.week_holder, textvariable=self.weekday_var, state="readonly",
                     values=DIAS_SEMANA).pack(fill="x")

        self.month_holder = tk.Frame(self.detail_row, bg=theme.CARD)
        self.month_holder.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        form_label(self.month_holder, "MES DEL AÑO").pack(fill="x", pady=(0, 5))
        ttk.Combobox(self.month_holder, textvariable=self.month_var, state="readonly",
                     values=["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
                             "Diciembre"]).pack(fill="x")

        self.quincenal_hint = tk.Label(
            self.detail_row, text="Se registrará los días 1 y 16 de cada mes.",
            bg=theme.CARD, fg=theme.MUTED, font=font(9), anchor="w",
        )
        self.quincenal_hint.grid(row=0, column=0, columnspan=3, sticky="ew", padx=(0, 8))

        self.normal_row = tk.Frame(form, bg=theme.CARD)
        self.normal_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.normal_row.columnconfigure(0, weight=1, uniform="rnorm")
        self.normal_row.columnconfigure(1, weight=1, uniform="rnorm")
        cat_holder = tk.Frame(self.normal_row, bg=theme.CARD)
        cat_holder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        form_label(cat_holder, "CATEGORÍA").pack(fill="x", pady=(0, 5))
        self.category_combo = ttk.Combobox(cat_holder, textvariable=self.category_var,
                                           state="readonly")
        self.category_combo.pack(fill="x")
        acc_holder = tk.Frame(self.normal_row, bg=theme.CARD)
        acc_holder.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        form_label(acc_holder, "CUENTA").pack(fill="x", pady=(0, 5))
        self.account_combo = ttk.Combobox(
            acc_holder, textvariable=self.account_var, state="readonly",
            values=[a["name"] for a in self.accounts],
        )
        self.account_combo.pack(fill="x")
        self.account_combo.bind("<<ComboboxSelected>>",
                                lambda _e: self._update_amount_label())

        self.transfer_row = tk.Frame(form, bg=theme.CARD)
        self.transfer_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.transfer_row.columnconfigure(0, weight=1, uniform="rtr")
        self.transfer_row.columnconfigure(1, weight=1, uniform="rtr")
        origin_holder = tk.Frame(self.transfer_row, bg=theme.CARD)
        origin_holder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        form_label(origin_holder, "CUENTA DE ORIGEN").pack(fill="x", pady=(0, 5))
        self.origin_combo = ttk.Combobox(
            origin_holder, textvariable=self.origin_var, state="readonly",
            values=[a["name"] for a in self.accounts],
        )
        self.origin_combo.pack(fill="x")
        dest_holder = tk.Frame(self.transfer_row, bg=theme.CARD)
        dest_holder.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        form_label(dest_holder, "CUENTA DE DESTINO").pack(fill="x", pady=(0, 5))
        self.dest_combo = ttk.Combobox(
            dest_holder, textvariable=self.dest_var, state="readonly",
            values=[a["name"] for a in self.accounts],
        )
        self.dest_combo.pack(fill="x")
        self.origin_combo.bind("<<ComboboxSelected>>",
                               lambda _e: self._update_amount_label())
        self.dest_combo.bind("<<ComboboxSelected>>",
                             lambda _e: self._update_amount_label())

        desc_holder = tk.Frame(form, bg=theme.CARD)
        desc_holder.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        form_label(desc_holder, "DESCRIPCIÓN (OPCIONAL)").pack(fill="x", pady=(0, 5))
        ttk.Entry(desc_holder, textvariable=self.desc_var).pack(fill="x")

        ttk.Checkbutton(form, text="Activa (generar movimientos pendientes)",
                        variable=self.active_var).grid(
            row=6, column=0, columnspan=2, sticky="w")

        ttk.Button(self.footer, text="Guardar recurrente", style="Primary.TButton",
                   command=self._save).pack(side="right")
        ttk.Button(self.footer, text=CANCEL, style="Secondary.TButton",
                   command=self._cancel).pack(side="right", padx=(0, 8))
        self.bind("<Return>", lambda _e: self._save())
        self._set_kind(self.kind_var.get(), initial=True)

    def _prefill(self, rule: dict | None):
        if not rule:
            self.account_var.set(self.accounts[0]["name"])
            self.origin_var.set(self.accounts[0]["name"])
            self.dest_var.set(self.accounts[1]["name"] if len(self.accounts) > 1 else "")
            self.category_var.set("Sin categoría")
            self._update_amount_label()
            return
        style = getattr(self.host_app, "number_format", "en")
        self.amount_var.set(money_input(rule["amount"], style))
        account = self.db.get_account(rule.get("account_id")) if rule.get("account_id") else None
        target = self.db.get_account(rule.get("transfer_account_id")) \
            if rule.get("transfer_account_id") else None
        if account:
            self.account_var.set(account["name"])
            self.origin_var.set(account["name"])
        if target:
            self.dest_var.set(target["name"])
        self.freq_var.set(FREQUENCY_LABELS.get(rule.get("frequency"), "Mensual"))
        day = int(rule.get("day") or 1)
        if rule.get("frequency") == "semanal":
            self.weekday_var.set(DIAS_SEMANA[day % 7])
        else:
            self.day_var.set(str(day))
        month = int(rule.get("month") or 1)
        month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
                       "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        self.month_var.set(month_names[month - 1])
        self._refresh_category_values()
        if rule.get("category_id"):
            category = self.db.get_category(rule["category_id"])
            if category:
                self.category_var.set(category["name"])
        self._update_amount_label()

    # ------------------------------------------------------------ interfaz
    def _set_kind(self, kind: str, initial: bool = False):
        self.kind_var.set(kind)
        for key, btn in self.kind_buttons.items():
            btn.configure(style="Primary.TButton" if key == kind else "Secondary.TButton")
        self._refresh_category_values()
        if kind == "transferencia":
            self.normal_row.grid_remove()
            self.transfer_row.grid()
            if not initial:
                if self.account_var.get():
                    self.origin_var.set(self.account_var.get())
                if not self.dest_var.get() or self.dest_var.get() == self.origin_var.get():
                    others = [a["name"] for a in self.accounts if a["name"] != self.origin_var.get()]
                    if others:
                        self.dest_var.set(others[0])
        else:
            self.transfer_row.grid_remove()
            self.normal_row.grid()
        self._update_amount_label()

    def _refresh_category_values(self):
        kind = "ingreso" if self.kind_var.get() == "ingreso" else "egreso"
        options = [c for c in self.categories if c["kind"] == kind]
        values = ["Sin categoría"] + [c["name"] for c in options]
        self.category_combo.configure(values=values)
        self._category_map = {c["name"]: c["id"] for c in options}
        if self.category_var.get() not in values:
            self.category_var.set("Sin categoría")

    def _on_frequency_change(self):
        label = self.freq_var.get()
        key = next((k for k, v in FREQUENCY_LABELS.items() if v == label), "mensual")
        self.day_holder.grid_remove()
        self.week_holder.grid_remove()
        self.month_holder.grid_remove()
        self.quincenal_hint.grid_remove()
        if key == "semanal":
            self.week_holder.grid()
            self.freq_hint.configure(text="Se repetirá cada semana en ese día.")
        elif key == "quincenal":
            self.quincenal_hint.grid()
            self.freq_hint.configure(text="Dos veces al mes (días 1 y 16).")
        elif key == "anual":
            self.day_holder.grid()
            self.month_holder.grid()
            self.freq_hint.configure(text="Una vez al año.")
        else:
            self.day_holder.grid()
            self.freq_hint.configure(text="Cada mes en ese día (se ajusta al último día).")

    def _account_for_var(self, var: tk.StringVar) -> dict | None:
        name = var.get()
        return next((a for a in self.accounts if a["name"] == name), None)

    def _update_amount_label(self):
        var = self.origin_var if self.kind_var.get() == "transferencia" else self.account_var
        account = self._account_for_var(var)
        base = getattr(self.host_app, "base_currency", "") or ""
        code = (account or {}).get("currency") or base
        self.amount_label.configure(text=f"MONTO ({code})" if code else "MONTO")

    def _selected_account_id(self, var: tk.StringVar) -> int | None:
        name = var.get()
        return next((a["id"] for a in self.accounts if a["name"] == name), None)

    def _save(self):
        try:
            amount = parse_amount(self.amount_var.get())
            start = parse_date(self.start_var.get()).isoformat()
            kind = self.kind_var.get()
            description = self.desc_var.get().strip()
            label = self.freq_var.get()
            frequency = next((k for k, v in FREQUENCY_LABELS.items() if v == label), "mensual")
            month = None
            if kind == "transferencia":
                account_id = self._selected_account_id(self.origin_var)
                dest_id = self._selected_account_id(self.dest_var)
                if not account_id or not dest_id:
                    raise ValueError("Selecciona la cuenta de origen y la de destino.")
                if account_id == dest_id:
                    raise ValueError("Las cuentas de origen y destino deben ser distintas.")
                category_id = None
                if not description:
                    description = "Transferencia recurrente"
            else:
                account_id = self._selected_account_id(self.account_var)
                if not account_id:
                    raise ValueError("Selecciona una cuenta.")
                category_id = self._category_map.get(self.category_var.get())
                if not description and category_id:
                    category = next((c for c in self.categories if c["id"] == category_id), None)
                    description = category["name"] if category else ""
                dest_id = None

            if frequency == "semanal":
                day = DIAS_SEMANA.index(self.weekday_var.get())
            elif frequency == "quincenal":
                day = 1
            else:
                try:
                    day = int(self.day_var.get())
                except ValueError:
                    raise ValueError("El día debe ser un número entre 1 y 31.")
                if not 1 <= day <= 31:
                    raise ValueError("El día debe estar entre 1 y 31.")
                if frequency == "anual":
                    month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
                                   "Diciembre"]
                    month = month_names.index(self.month_var.get()) + 1
                    max_day = 29 if month == 2 else 30 if month in (4, 6, 9, 11) else 31
                    if day > max_day:
                        raise ValueError("Ese día no existe en el mes elegido.")

            if self.rule:
                self.db.update_recurring(
                    self.rule["id"], description, kind, amount, category_id,
                    account_id, dest_id, frequency, day, start, month,
                    active=self.active_var.get(),
                )
            else:
                self.db.add_recurring(
                    description, kind, amount, category_id, account_id, dest_id,
                    frequency, day, start, month, active=self.active_var.get(),
                )
        except (ValueError, sqlite3.Error) as exc:
            self.show_error(str(exc))
            return
        if self.on_saved:
            self.on_saved()
        self._finish(True)


class RuleDialog(BaseDialog):
    """Regla automática: si la descripción contiene un texto, categoriza."""

    def __init__(self, parent, db, rule: dict | None = None, on_saved=None):
        super().__init__(parent, "Editar regla" if rule else "Nueva regla automática", 540)
        self.db = db
        self.rule = rule
        self.on_saved = on_saved

        tk.Label(
            self.body,
            text="Si la descripción o las notas de un movimiento nuevo contienen el "
                 "texto indicado, se aplicarán la categoría y/o la cuenta elegidas. "
                 "No distingue mayúsculas. Las reglas más antiguas tienen prioridad.",
            bg=theme.CARD, fg=theme.MUTED, font=font(9), anchor="w",
            justify="left", wraplength=470,
        ).pack(fill="x", pady=(0, 12))

        form_label(self.body, "SI LA DESCRIPCIÓN CONTIENE").pack(fill="x", pady=(0, 5))
        self.match_var = tk.StringVar(value=rule.get("match_text", "") if rule else "")
        entry = ttk.Entry(self.body, textvariable=self.match_var)
        entry.pack(fill="x")
        entry.focus_set()
        tk.Label(self.body, text="Ejemplo: NETFLIX, supermercado, alquiler…",
                 bg=theme.CARD, fg=theme.SUBTLE, font=font(8), anchor="w").pack(
            fill="x", pady=(4, 0))

        form_label(self.body, "ASIGNAR CATEGORÍA").pack(fill="x", pady=(12, 5))
        categories = self.db.categories(include_archived=False)
        names = [c["name"] for c in categories]
        self.category_map = {"No cambiar": None}
        values = ["No cambiar"]
        for category in categories:
            display = category["name"]
            if names.count(category["name"]) > 1:
                display += " (ingreso)" if category["kind"] == "ingreso" else " (gasto)"
            self.category_map[display] = category["id"]
            values.append(display)
        self.category_var = tk.StringVar(value="No cambiar")
        self.category_combo = ttk.Combobox(
            self.body, textvariable=self.category_var, state="readonly", values=values
        )
        self.category_combo.pack(fill="x")

        form_label(self.body, "ASIGNAR CUENTA").pack(fill="x", pady=(12, 5))
        accounts = self.db.accounts()
        self.account_map = {"No cambiar": None}
        for account in accounts:
            display = account["name"]
            if account.get("currency"):
                display += f" ({account['currency']})"
            self.account_map[display] = account["id"]
        self.account_var = tk.StringVar(value="No cambiar")
        ttk.Combobox(
            self.body, textvariable=self.account_var, state="readonly",
            values=list(self.account_map.keys()),
        ).pack(fill="x")

        self.active_var = tk.BooleanVar(value=bool(rule.get("active", 1)) if rule else True)
        ttk.Checkbutton(self.body, text="Regla activa",
                        variable=self.active_var).pack(anchor="w", pady=(14, 0))

        if rule:
            if rule.get("category_id"):
                display = next(
                    (k for k, v in self.category_map.items() if v == rule["category_id"]),
                    "No cambiar",
                )
                self.category_var.set(display)
            if rule.get("account_id"):
                display = next(
                    (k for k, v in self.account_map.items()
                     if v == rule["account_id"]),
                    "No cambiar",
                )
                self.account_var.set(display)

        ttk.Button(self.footer, text="Guardar regla", style="Primary.TButton",
                   command=self._save).pack(side="right")
        ttk.Button(self.footer, text=CANCEL, style="Secondary.TButton",
                   command=self._cancel).pack(side="right", padx=(0, 8))
        self.bind("<Return>", lambda _e: self._save())

    def _save(self):
        text = self.match_var.get().strip()
        category_id = self.category_map.get(self.category_var.get())
        account_id = self.account_map.get(self.account_var.get())
        try:
            if self.rule:
                self.db.update_rule(
                    self.rule["id"], text, category_id, account_id,
                    active=self.active_var.get(),
                )
            else:
                self.db.add_rule(text, category_id, account_id,
                                 active=self.active_var.get())
        except (ValueError, sqlite3.Error) as exc:
            self.show_error(str(exc))
            return
        if self.on_saved:
            self.on_saved()
        self._finish(True)
