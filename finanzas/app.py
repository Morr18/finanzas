"""Ventana principal de Finanzas."""
from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import ttk

from . import theme
from .db import Database
from .dialogs import BaseDialog, TransactionDialog, ask_confirm
from .theme import font
from .utils import currency_symbol, localize_number, money as format_money, today_iso
from .views import (
    AccountsView, BudgetsView, CategoriesView, DashboardView, RecurringView,
    ReportsView, RulesView, SettingsView, TransactionsView,
)
from .widgets import ScrollFrame

PAGES = [
    ("resumen", "Resumen", DashboardView),
    ("movimientos", "Movimientos", TransactionsView),
    ("recurrentes", "Recurrentes", RecurringView),
    ("presupuestos", "Presupuestos", BudgetsView),
    ("categorias", "Categorías", CategoriesView),
    ("cuentas", "Cuentas", AccountsView),
    ("reglas", "Reglas", RulesView),
    ("reportes", "Reportes", ReportsView),
    ("ajustes", "Ajustes", SettingsView),
]


class App(tk.Tk):
    def __init__(self, db_path=None):
        super().__init__()
        self.db = Database(db_path)
        theme.set_mode(self.db.get_setting("theme", "light"))
        theme.apply_theme(self)
        self.currency = self.db.get_setting("currency", "$") or "$"
        self.base_currency = self.db.base_currency()
        self.display_currency = self._load_display_currency()
        style = self.db.get_setting("number_format", "en")
        self.number_format = style if style in ("en", "es") else "en"
        self.views: dict[str, tk.Frame] = {}
        self.current: str | None = None
        self._toast: tk.Frame | None = None
        self._toast_job = None
        self._undo_stack: list[tuple[str, object]] = []

        self.title("Finanzas — Control personal")
        self._setup_window()
        self._build_layout()
        self._bind_shortcuts()
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")
        self.bind_all("<Button-4>", self._on_wheel, add="+")
        self.bind_all("<Button-5>", self._on_wheel, add="+")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        last_view = self.db.get_setting("last_view", "resumen")
        if last_view not in {key for key, _label, _view in PAGES}:
            last_view = "resumen"
        created = 0
        try:
            created = self.db.process_recurring()
        except sqlite3.Error:
            created = 0
        self.show(last_view)
        if created:
            self.refresh_current()
            self.update_sidebar()
            self.toast(
                f"{created} movimiento{'s' if created != 1 else ''} recurrente"
                f"{'s' if created != 1 else ''} registrado{'s' if created != 1 else ''}"
            )


    # ------------------------------------------------------------ ventana
    def _setup_window(self):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(1320, screen_w - 60)
        height = min(860, screen_h - 80)
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 3)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min(1180, screen_w - 40), min(700, screen_h - 60))

    def _build_layout(self):
        shell = tk.Frame(self, bg=theme.BG)
        shell.pack(fill="both", expand=True)

        sidebar = tk.Frame(shell, bg=theme.SIDEBAR, width=234)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # logo
        logo = tk.Frame(sidebar, bg=theme.SIDEBAR)
        logo.pack(fill="x", padx=20, pady=(22, 20))
        mark = tk.Label(logo, text="$", bg=theme.PRIMARY, fg=theme.ON_PRIMARY,
                        font=font(17, "bold"), width=2, height=1)
        mark.pack(side="left")
        text = tk.Frame(logo, bg=theme.SIDEBAR)
        text.pack(side="left", padx=(10, 0))
        tk.Label(text, text="Finanzas", bg=theme.SIDEBAR, fg=theme.SIDEBAR_FG,
                 font=font(14, "bold"), anchor="w").pack(fill="x")
        tk.Label(text, text="Control personal", bg=theme.SIDEBAR,
                 fg=theme.SIDEBAR_MUTED, font=font(8), anchor="w").pack(fill="x")

        tk.Label(sidebar, text="MENÚ", bg=theme.SIDEBAR, fg=theme.SIDEBAR_MUTED,
                 font=font(7, "bold"), anchor="w").pack(fill="x", padx=22, pady=(0, 6))

        self.nav_buttons: dict[str, ttk.Button] = {}
        for key, label, _view in PAGES:
            if key == "ajustes":
                tk.Frame(sidebar, bg=theme.SIDEBAR, height=10).pack(fill="x")
            button = ttk.Button(sidebar, text=f"   {label}", style="Nav.TButton",
                                command=lambda k=key: self.show(k))
            button.pack(fill="x", padx=12, pady=1)
            self.nav_buttons[key] = button

        footer = tk.Frame(sidebar, bg=theme.SIDEBAR)
        footer.pack(side="bottom", fill="x", padx=12, pady=14)
        card = tk.Frame(footer, bg=theme.SIDEBAR_CARD)
        card.pack(fill="x")
        tk.Label(card, text="BALANCE TOTAL", bg=theme.SIDEBAR_CARD,
                 fg=theme.SIDEBAR_MUTED, font=font(7, "bold"), anchor="w").pack(
            fill="x", padx=12, pady=(10, 0))
        self.sidebar_balance = tk.Label(card, text="—", bg=theme.SIDEBAR_CARD,
                                        fg=theme.SIDEBAR_FG, font=font(15, "bold"), anchor="w")
        self.sidebar_balance.pack(fill="x", padx=12)
        self.sidebar_hint = tk.Label(card, text="", bg=theme.SIDEBAR_CARD,
                                     fg=theme.SIDEBAR_MUTED, font=font(8), anchor="w")
        self.sidebar_hint.pack(fill="x", padx=12, pady=(0, 10))

        main = tk.Frame(shell, bg=theme.BG)
        main.pack(side="left", fill="both", expand=True)

        header = tk.Frame(main, bg=theme.BG)
        header.pack(fill="x", padx=24, pady=(18, 0))
        titles = tk.Frame(header, bg=theme.BG)
        titles.pack(side="left")
        self.title_lbl = tk.Label(titles, text="", bg=theme.BG, fg=theme.TEXT,
                                  font=font(18, "bold"), anchor="w")
        self.title_lbl.pack(fill="x")
        self.subtitle_lbl = tk.Label(titles, text="", bg=theme.BG, fg=theme.MUTED,
                                     font=font(9), anchor="w")
        self.subtitle_lbl.pack(fill="x", pady=(2, 0))

        actions = tk.Frame(header, bg=theme.BG)
        actions.pack(side="right")
        ttk.Button(actions, text="+ Nuevo movimiento", style="Primary.TButton",
                   command=self.new_transaction).pack(side="right", padx=(10, 0))
        self.display_var = tk.StringVar(value=self.display_currency_code())
        self.display_combo = ttk.Combobox(
            actions, textvariable=self.display_var, state="readonly", width=9,
            values=self.available_display_currencies(),
        )
        self.display_combo.pack(side="right")
        self.display_combo.bind("<<ComboboxSelected>>", self._on_display_change)
        self.display_rate_lbl = tk.Label(
            actions, text="", bg=theme.BG, fg=theme.MUTED, font=font(8), anchor="e",
        )
        self.display_rate_lbl.pack(side="right", padx=(0, 8))
        tk.Label(actions, text="Ver en", bg=theme.BG, fg=theme.MUTED,
                 font=font(8, "bold")).pack(side="right", padx=(0, 6))
        self._refresh_display_controls()

        self.content = tk.Frame(main, bg=theme.BG)
        self.content.pack(fill="both", expand=True, padx=24, pady=(16, 20))

    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda _e: self.new_transaction())
        self.bind("<Control-f>", lambda _e: self._focus_search())
        self.bind("<Control-z>", self._undo_shortcut)
        self.bind("<F5>", lambda _e: self.refresh_current())
        self.bind("<Control-q>", lambda _e: self._on_close())

    # ------------------------------------------------------------ navegación
    def show(self, key: str):
        page = next((p for p in PAGES if p[0] == key), None)
        if page is None:
            return
        if self.current == key and key in self.views:
            view = self.views[key]
            if hasattr(view, "confirm_leave") and not view.confirm_leave():
                return
            view.refresh()
            return
        if self.current and self.current in self.views:
            current_view = self.views[self.current]
            if hasattr(current_view, "confirm_leave") and not current_view.confirm_leave():
                return
            current_view.pack_forget()
        if key not in self.views:
            self.views[key] = page[2](self)
        view = self.views[key]
        view.pack(fill="both", expand=True)
        self.current = key
        self.title_lbl.configure(text=page[2].title or page[1])
        self.subtitle_lbl.configure(text=page[2].subtitle)
        for nav_key, button in self.nav_buttons.items():
            button.configure(style="NavActive.TButton" if nav_key == key
                             else "Nav.TButton")
        view.refresh()
        self.update_sidebar()
        self.db.set_setting("last_view", key)

    def reload_all(self):
        current = self.current or "resumen"
        self._cancel_toast_job()
        self.currency = self.db.get_setting("currency", "$") or "$"
        self.base_currency = self.db.base_currency()
        self.display_currency = self._load_display_currency()
        style = self.db.get_setting("number_format", "en")
        self.number_format = style if style in ("en", "es") else "en"
        wanted_mode = "dark" if self.db.get_setting("theme", "light") == "dark" else "light"
        if wanted_mode != theme.MODE and not BaseDialog.has_open():
            self.set_theme(wanted_mode, persist=False, notify=False)
            return
        self.current = None
        self._undo_stack.clear()  # los datos se reemplazaron o ampliaron
        self._refresh_display_controls()
        for view in self.views.values():
            view.destroy()
        self.views.clear()
        self.show(current)

    def _rebuild_ui(self, current: str):
        """Reconstruye toda la interfaz para aplicar un tema nuevo."""
        if BaseDialog.has_open():
            BaseDialog.focus_open()
            self.toast("Cierra la ventana abierta para cambiar el tema", "error")
            return
        current = current if current in {p[0] for p in PAGES} else "resumen"
        self._cancel_toast_job()
        self._undo_stack.clear()
        for view in self.views.values():
            view.destroy()
        self.views.clear()
        for child in list(self.winfo_children()):
            if isinstance(child, tk.Toplevel):
                continue
            child.destroy()
        self._toast = None
        theme.apply_theme(self)
        self._build_layout()
        self.current = None
        self.show(current)

    def set_theme(self, mode: str, persist: bool = True, notify: bool = True):
        mode = "dark" if str(mode).lower() == "dark" else "light"
        if mode == theme.MODE:
            return
        if BaseDialog.has_open():
            # No cambiar la paleta si no se puede reconstruir la interfaz:
            # quedaría una ventana con colores mezclados.
            BaseDialog.focus_open()
            self.toast("Cierra la ventana abierta para cambiar el tema", "error")
            return
        if persist:
            self.db.set_setting("theme", mode)
        theme.set_mode(mode)
        self._rebuild_ui(self.current or "resumen")
        if notify:
            self.toast("Tema oscuro activado" if mode == "dark" else "Tema claro activado")

    def refresh_current(self):
        if self.current and self.current in self.views:
            self.views[self.current].refresh()
        self.update_sidebar()

    def update_sidebar(self):
        balances = self.db.account_balances()
        total = sum(a["base_balance"] for a in balances)
        self.sidebar_balance.configure(
            text=self.money(total), fg=theme.GREEN if total >= 0 else theme.RED
        )
        count = len(balances)
        hint = f"{count} cuenta{'s' if count != 1 else ''} activa{'s' if count != 1 else ''}"
        if self.display_currency:
            hint += f" · en {self.display_currency}"
        elif self.db.has_foreign_accounts():
            hint += f" · base {self.base_currency}"
        self.sidebar_hint.configure(text=hint)

    # ------------------------------------------------------------ recurrentes
    def process_recurring(self, notify: bool = True, manual: bool = False,
                          refresh: bool = True) -> int:
        try:
            created = self.db.process_recurring()
        except sqlite3.Error as exc:
            if notify:
                self.toast(f"No se pudieron generar los recurrentes: {exc}", "error")
            return 0
        if created:
            if refresh:
                self.refresh_current()
                self.update_sidebar()
            if notify:
                self.toast(
                    f"{created} movimiento{'s' if created != 1 else ''} recurrente"
                    f"{'s' if created != 1 else ''} registrado{'s' if created != 1 else ''}"
                )
        elif manual and notify:
            self.toast("No hay movimientos recurrentes pendientes", "info")
        return created

    # ------------------------------------------------------------ utilidades
    def display_currency_code(self) -> str:
        """Moneda en la que se muestran los montos (la base si no hay selección)."""
        return self.display_currency or self.base_currency

    def available_display_currencies(self) -> list[str]:
        base = self.base_currency.upper()
        codes = [c for c in self.db.currencies_with_rates() if c.upper() != base]
        return [self.base_currency] + sorted(codes)

    def _load_display_currency(self) -> str:
        """Lee la preferencia y la descarta si ya no tiene tasa disponible."""
        base = self.db.base_currency().upper()
        code = (self.db.get_setting("display_currency", "") or "").strip().upper()
        if not code or code == base:
            return ""
        if code not in {c.upper() for c in self.db.currencies_with_rates()}:
            return ""
        return code

    def display_symbol(self) -> str:
        if not self.display_currency:
            return self.currency
        return currency_symbol(self.display_currency, self.currency)

    def display_rate_text(self) -> str:
        """Texto corto con la tasa aplicada, por ejemplo «1 USD = 18.00 MXN»."""
        if not self.display_currency:
            return ""
        micros = self.db.fx_rate_micros(self.display_currency, today_iso())
        rate = micros / 1_000_000
        body = localize_number(f"{rate:,.4f}", self.number_format)
        body = body.rstrip("0").rstrip(".,") or "0"
        return f"1 {self.display_currency} = {body} {self.base_currency}"

    def convert_display(self, cents: int, date: str | None = None) -> int:
        """Convierte centavos de la moneda base a la moneda de visualización."""
        cents = int(cents or 0)
        if not self.display_currency:
            return cents
        return self.db.from_base(cents, self.display_currency, date or today_iso())

    def to_base_display(self, cents: int, date: str | None = None) -> int:
        """Convierte centavos de la moneda de visualización a la moneda base."""
        cents = int(cents or 0)
        if not self.display_currency:
            return cents
        return self.db.to_base(cents, self.display_currency, date or today_iso())

    def convert_native(self, cents: int, currency: str | None = None,
                       date: str | None = None) -> int:
        """Convierte un monto nativo a la moneda de visualización."""
        cents = int(cents or 0)
        if not self.display_currency:
            return cents
        code = (currency or "").strip().upper()
        target = self.display_currency.upper()
        source = code or self.base_currency.upper()
        if source == target:
            return cents
        return self.db.convert_between(cents, code, target, date or today_iso())

    def money_display(self, cents: int, plus: bool = False,
                      date: str | None = None) -> str:
        """Formatea un monto que está en la moneda base."""
        value = self.convert_display(cents, date)
        return format_money(value, self.display_symbol(), plus=plus,
                            style=self.number_format)

    def money_native(self, cents: int, currency: str | None = None,
                     date: str | None = None, plus: bool = False) -> str:
        """Formatea un monto en la moneda de su cuenta y lo convierte si aplica."""
        code = (currency or "").strip().upper()
        if not self.display_currency:
            symbol = (self.currency if not code or code == self.base_currency.upper()
                      else currency_symbol(code, self.currency))
            return format_money(cents, symbol, plus=plus, style=self.number_format)
        value = self.convert_native(cents, code, date)
        return format_money(value, self.display_symbol(), plus=plus,
                            style=self.number_format)

    def money_original(self, cents: int, currency: str | None = None,
                       plus: bool = False) -> str:
        """Formatea un monto en su moneda original, sin convertir."""
        code = (currency or "").strip().upper()
        symbol = (self.currency if not code or code == self.base_currency.upper()
                  else currency_symbol(code, self.currency))
        return format_money(cents, symbol, plus=plus, style=self.number_format)

    def money(self, cents: int, plus: bool = False, currency: str | None = None) -> str:
        if currency is None:
            return self.money_display(cents, plus=plus)
        return self.money_native(cents, currency=currency, plus=plus)

    def set_display_currency(self, code: str, persist: bool = True,
                             notify: bool = True) -> None:
        """Cambia la moneda de visualización sin modificar los datos guardados."""
        base = self.base_currency.upper()
        code = (code or "").strip().upper()
        if code == base:
            code = ""
        if code and code not in {c.upper() for c in self.db.currencies_with_rates()}:
            if notify:
                self.toast(f"No hay una tasa registrada para {code}", "error")
            self._refresh_display_controls()
            return
        if code == self.display_currency:
            self._refresh_display_controls()
            return
        self.display_currency = code
        if persist:
            self.db.set_setting("display_currency", code)
        self._refresh_display_controls()
        self.refresh_current()
        self.update_sidebar()
        if notify:
            if code:
                self.toast(f"Montos convertidos a {code} · {self.display_rate_text()}")
            else:
                self.toast(f"Montos en la moneda base ({self.base_currency})")

    def ensure_display_currency(self) -> None:
        """Vuelve a la moneda base si la moneda elegida ya no tiene tasa."""
        code = self._load_display_currency()
        if code == self.display_currency:
            return
        self.display_currency = code
        self.db.set_setting("display_currency", code)
        self._refresh_display_controls()
        self.update_sidebar()

    def _on_display_change(self, _event=None):
        self.set_display_currency(self.display_var.get())

    def _refresh_display_controls(self) -> None:
        combo = getattr(self, "display_combo", None)
        if combo is None:
            return
        combo.configure(values=self.available_display_currencies())
        self.display_var.set(self.display_currency_code())
        rate_text = self.display_rate_text()
        if rate_text:
            self.display_rate_lbl.configure(
                text=rate_text + " · solo visualización", fg=theme.MUTED
            )
        else:
            self.display_rate_lbl.configure(text="", fg=theme.MUTED)

    @staticmethod
    def color_for(cents: int) -> str:
        return theme.GREEN if cents >= 0 else theme.RED

    def _focus_search(self):
        view = self.views.get("movimientos")
        if self.current != "movimientos":
            self.show("movimientos")
            view = self.views.get("movimientos")
        if view is not None and hasattr(view, "focus_search"):
            view.focus_search()

    # ------------------------------------------------------------ acciones
    def new_transaction(self):
        if TransactionDialog(self, self.db).run():
            self.refresh_current()
        self.update_sidebar()

    def load_demo_data(self):
        if self.db.has_transactions():
            if not ask_confirm(
                self, "Cargar datos de ejemplo",
                "Se agregarán movimientos de ejemplo a tus datos actuales. "
                "No se borrará nada. ¿Continuar?",
                confirm_text="Cargar ejemplos", danger=False,
            ):
                return
        self.db.seed_demo()
        self.reload_all()
        self.toast("Datos de ejemplo cargados")

    def _cancel_toast_job(self):
        if self._toast_job is not None:
            try:
                self.after_cancel(self._toast_job)
            except tk.TclError:
                pass
            self._toast_job = None

    def toast(self, message: str, kind: str = "ok", action_text: str = "",
              action=None):
        self._cancel_toast_job()
        if self._toast is not None:
            try:
                self._toast.destroy()
            except tk.TclError:
                pass
        dot_color = {"ok": theme.GREEN, "error": theme.RED, "info": theme.BLUE}.get(kind)
        frame = tk.Frame(self, bg=theme.TOAST_BG, padx=14, pady=10)
        dot = tk.Canvas(frame, width=10, height=10, bg=theme.TOAST_BG, highlightthickness=0)
        dot.create_oval(2, 2, 9, 9, fill=dot_color, outline="")
        dot.pack(side="left", padx=(0, 9))
        tk.Label(frame, text=message, bg=theme.TOAST_BG, fg=theme.TOAST_TEXT,
                 font=font(9)).pack(side="left")
        if action_text and action:
            button = tk.Label(frame, text=action_text, bg=theme.TOAST_BG, fg=theme.TOAST_ACTION,
                              font=font(9, "bold"), cursor="hand2", padx=8)
            button.pack(side="left", padx=(10, 0))

            def _run_action():
                self._cancel_toast_job()
                try:
                    frame.destroy()
                except tk.TclError:
                    pass
                action()

            button.bind("<Button-1>", lambda _e: _run_action())
        frame.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")
        frame.lift()
        self._toast = frame

        def _dismiss(_event=None):
            self._cancel_toast_job()
            try:
                frame.destroy()
            except tk.TclError:
                pass

        frame.bind("<Button-1>", _dismiss)

        def _close():
            self._toast_job = None
            try:
                frame.destroy()
            except tk.TclError:
                pass

        self._toast_job = self.after(6500 if action else 3800, _close)

    # ------------------------------------------------------------ eventos
    def _on_wheel(self, event):
        # Se usa event.widget (el widget bajo el puntero) en lugar de
        # winfo_containing(): la lista desplegable de un Combobox es un Toplevel
        # interno llamado "popdown" que Tkinter no registra y winfo_containing()
        # lanza KeyError: 'popdown'.
        try:
            widget = event.widget
            while widget is not None:
                if isinstance(widget, (ttk.Treeview, tk.Text, tk.Listbox)):
                    return
                if isinstance(widget, ScrollFrame):
                    if getattr(event, "num", None) == 4:
                        step = -3
                    elif getattr(event, "num", None) == 5:
                        step = 3
                    else:
                        step = -3 if getattr(event, "delta", 0) > 0 else 3
                    widget.canvas.yview_scroll(step, "units")
                    return
                widget = widget.master
        except (KeyError, tk.TclError):
            # Nunca dejar que un evento de rueda rompa la interfaz.
            return

    # ------------------------------------------------------------ deshacer
    def push_undo(self, label: str, fn):
        """Registra una acción reversible (máximo 20) y devuelve la entrada."""
        entry = (label, fn)
        self._undo_stack.append(entry)
        del self._undo_stack[:-20]
        return entry

    def undo_entry(self, entry) -> None:
        try:
            self._undo_stack.remove(entry)
        except ValueError:
            pass
        label, fn = entry
        try:
            fn()
        except Exception as exc:  # la interfaz nunca debe romperse al deshacer
            self.toast(f"No se pudo deshacer: {exc}", "error")
            return
        self.refresh_current()
        self.update_sidebar()
        self.toast(f"Deshecho: {label}")

    def undo_last(self) -> None:
        if not self._undo_stack:
            self.toast("No hay acciones para deshacer", "info")
            return
        self.undo_entry(self._undo_stack[-1])

    def undo_toast(self, message: str, label: str, fn) -> None:
        entry = self.push_undo(label, fn)
        self.toast(message, action_text="Deshacer",
                   action=lambda: self.undo_entry(entry))

    def _undo_shortcut(self, _event=None):
        widget = self.focus_get()
        if isinstance(widget, (tk.Entry, ttk.Entry, tk.Text)):
            return  # dejar que el campo maneje el texto
        self.undo_last()

    def _on_close(self):
        if BaseDialog.has_open():
            BaseDialog.focus_open()
            self.toast("Cierra la ventana abierta para salir", "error")
            return
        if self.current and self.current in self.views:
            view = self.views[self.current]
            if hasattr(view, "confirm_leave") and not view.confirm_leave():
                return
        self._cancel_toast_job()
        self.db.close()
        self.destroy()
