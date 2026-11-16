"""Ajustes, respaldos y mantenimiento de datos."""
from __future__ import annotations

import datetime as dt
import sqlite3
import subprocess
import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import filedialog, ttk

from .. import __version__, theme
from ..dialogs import ask_confirm
from ..theme import font
from ..utils import localize_number, parse_date
from ..widgets import Card, ScrollFrame, card_title
from . import BaseView

NUMBER_LABELS = {
    "en": "1,234.56 (inglés)",
    "es": "1.234,56 (español)",
}
THEME_LABELS = {"Claro": "light", "Oscuro": "dark"}
THEME_VALUES = {value: label for label, value in THEME_LABELS.items()}


def _parse_rate(text: str) -> Decimal:
    raw = (text or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        raise ValueError("Escribe el tipo de cambio.")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ValueError("El tipo de cambio no es válido. Ejemplo: 1.10")
    if value <= 0:
        raise ValueError("El tipo de cambio debe ser mayor que cero.")
    return value


class SettingsView(BaseView):
    title = "Ajustes"
    subtitle = "Personaliza la aplicación y protege tus datos"

    def __init__(self, app):
        super().__init__(app)
        self._build()

    def refresh(self):
        self.currency_var.set(self.app.currency)
        self.number_var.set(NUMBER_LABELS.get(self.app.number_format, NUMBER_LABELS["en"]))
        self.theme_var.set(THEME_VALUES.get(theme.MODE, "Claro"))
        self.base_var.set(self.app.base_currency)
        self._refresh_display_options()
        self._refresh_rates()

    def _build(self):
        scroll = ScrollFrame(self, bg=theme.BG)
        scroll.pack(fill="both", expand=True)
        body = scroll.body
        body.columnconfigure(0, weight=1)

        # ---- apariencia
        theme_card = Card(body, padding=18)
        theme_card.grid(row=0, column=0, sticky="ew")
        card_title(theme_card.inner, "Apariencia",
                   "Cambia entre modo claro y oscuro; la elección se recuerda"
                   ).pack(fill="x")
        theme_row = tk.Frame(theme_card.inner, bg=theme.CARD)
        theme_row.pack(fill="x", pady=(12, 0))
        tk.Label(theme_row, text="TEMA", bg=theme.CARD, fg=theme.MUTED,
                 font=font(8, "bold")).pack(side="left", padx=(0, 10))
        self.theme_var = tk.StringVar(value=THEME_VALUES.get(theme.MODE, "Claro"))
        theme_combo = ttk.Combobox(
            theme_row, textvariable=self.theme_var, state="readonly", width=14,
            values=list(THEME_LABELS.keys()),
        )
        theme_combo.pack(side="left")
        theme_combo.bind("<<ComboboxSelected>>", self._change_theme)
        tk.Label(theme_row, text="La interfaz se reconstruye al instante.",
                 bg=theme.CARD, fg=theme.MUTED, font=font(8)).pack(side="left", padx=10)

        # ---- moneda y formato
        currency_card = Card(body, padding=18)
        currency_card.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        card_title(currency_card.inner, "Moneda y formato",
                   "Símbolo, separadores y moneda base para consolidar saldos"
                   ).pack(fill="x")
        row = tk.Frame(currency_card.inner, bg=theme.CARD)
        row.pack(fill="x", pady=(12, 0))
        tk.Label(row, text="SÍMBOLO", bg=theme.CARD, fg=theme.MUTED,
                 font=font(8, "bold")).pack(side="left", padx=(0, 8))
        self.currency_var = tk.StringVar(value=self.app.currency)
        entry = ttk.Entry(row, textvariable=self.currency_var, width=8)
        entry.pack(side="left")
        ttk.Button(row, text="Guardar", style="Primary.TButton",
                   command=self._save_currency).pack(side="left", padx=8)
        tk.Label(row, text="Ejemplos: $, €, S/, Mex$, US$", bg=theme.CARD,
                 fg=theme.MUTED, font=font(8)).pack(side="left", padx=6)

        format_row = tk.Frame(currency_card.inner, bg=theme.CARD)
        format_row.pack(fill="x", pady=(12, 0))
        tk.Label(format_row, text="FORMATO DE NÚMEROS", bg=theme.CARD, fg=theme.MUTED,
                 font=font(8, "bold")).pack(side="left", padx=(0, 10))
        self.number_var = tk.StringVar()
        number_combo = ttk.Combobox(
            format_row, textvariable=self.number_var, state="readonly", width=22,
            values=[NUMBER_LABELS["en"], NUMBER_LABELS["es"]],
        )
        number_combo.pack(side="left")
        number_combo.bind("<<ComboboxSelected>>", self._change_number_format)
        tk.Label(format_row, text="Solo cambia cómo se muestran los montos; los datos "
                                  "se guardan igual.",
                 bg=theme.CARD, fg=theme.MUTED, font=font(8)).pack(side="left", padx=10)

        base_row = tk.Frame(currency_card.inner, bg=theme.CARD)
        base_row.pack(fill="x", pady=(12, 0))
        tk.Label(base_row, text="MONEDA BASE", bg=theme.CARD, fg=theme.MUTED,
                 font=font(8, "bold")).pack(side="left", padx=(0, 8))
        self.base_var = tk.StringVar(value=self.app.base_currency)
        ttk.Entry(base_row, textvariable=self.base_var, width=8).pack(side="left")
        ttk.Button(base_row, text="Guardar base", style="Secondary.TButton",
                   command=self._save_base).pack(side="left", padx=8)
        tk.Label(base_row, text="Código ISO (USD, EUR…). Se usa para consolidar cuentas "
                                "en otras monedas.",
                 bg=theme.CARD, fg=theme.MUTED, font=font(8)).pack(side="left", padx=6)

        display_row = tk.Frame(currency_card.inner, bg=theme.CARD)
        display_row.pack(fill="x", pady=(12, 0))
        tk.Label(display_row, text="MOSTRAR MONTOS EN", bg=theme.CARD, fg=theme.MUTED,
                 font=font(8, "bold")).pack(side="left", padx=(0, 8))
        self.display_var = tk.StringVar(value=self.app.display_currency_code())
        self.display_combo = ttk.Combobox(
            display_row, textvariable=self.display_var, state="readonly", width=10,
            values=self.app.available_display_currencies(),
        )
        self.display_combo.pack(side="left")
        self.display_combo.bind("<<ComboboxSelected>>", self._change_display)
        self.display_hint = tk.Label(
            display_row, text="", bg=theme.CARD, fg=theme.MUTED, font=font(8),
        )
        self.display_hint.pack(side="left", padx=10)

        # ---- tipos de cambio
        fx_card = Card(body, padding=18)
        fx_card.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        card_title(fx_card.inner, "Tipos de cambio",
                   "Convierte los montos de cada cuenta a la moneda base"
                   ).pack(fill="x")
        self.fx_hint = tk.Label(
            fx_card.inner,
            text="1 unidad de la moneda extranjera = X unidades de la moneda base. "
                 "Ejemplo: 1 EUR = 1.10 USD.",
            bg=theme.CARD, fg=theme.MUTED, font=font(9), anchor="w",
            wraplength=760, justify="left",
        )
        self.fx_hint.pack(fill="x", pady=(10, 8))

        holder = tk.Frame(fx_card.inner, bg=theme.CARD)
        holder.pack(fill="x")
        self.rates_tree = ttk.Treeview(
            holder, columns=("currency", "date", "rate"), show="headings",
            height=5, selectmode="browse",
        )
        self.rates_tree.heading("currency", text="Moneda", anchor="w")
        self.rates_tree.heading("date", text="Fecha", anchor="w")
        self.rates_tree.heading("rate", text="Tasa", anchor="e")
        self.rates_tree.column("currency", width=100, anchor="w")
        self.rates_tree.column("date", width=120, anchor="w")
        self.rates_tree.column("rate", width=220, anchor="e", stretch=True)
        vsb = ttk.Scrollbar(holder, orient="vertical", command=self.rates_tree.yview)
        self.rates_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.rates_tree.pack(side="left", fill="x", expand=True)

        rate_form = tk.Frame(fx_card.inner, bg=theme.CARD)
        rate_form.pack(fill="x", pady=(10, 0))
        tk.Label(rate_form, text="MONEDA", bg=theme.CARD, fg=theme.MUTED,
                 font=font(8, "bold")).pack(side="left", padx=(0, 5))
        self.rate_currency_var = tk.StringVar()
        ttk.Entry(rate_form, textvariable=self.rate_currency_var, width=8).pack(side="left")
        tk.Label(rate_form, text="FECHA", bg=theme.CARD, fg=theme.MUTED,
                 font=font(8, "bold")).pack(side="left", padx=(10, 5))
        self.rate_date_var = tk.StringVar(value=dt.date.today().strftime("%d/%m/%Y"))
        ttk.Entry(rate_form, textvariable=self.rate_date_var, width=12).pack(side="left")
        tk.Label(rate_form, text="TASA", bg=theme.CARD, fg=theme.MUTED,
                 font=font(8, "bold")).pack(side="left", padx=(10, 5))
        self.rate_value_var = tk.StringVar()
        ttk.Entry(rate_form, textvariable=self.rate_value_var, width=12).pack(side="left")
        ttk.Button(rate_form, text="Guardar tasa", style="Primary.TButton",
                   command=self._save_rate).pack(side="left", padx=8)
        ttk.Button(rate_form, text="Eliminar seleccionada", style="DangerLink.TButton",
                   command=self._delete_rate).pack(side="left")
        self.fx_status = tk.Label(
            fx_card.inner, text="", bg=theme.CARD, fg=theme.SUBTLE, font=font(8),
            anchor="w", wraplength=760, justify="left",
        )
        self.fx_status.pack(fill="x", pady=(6, 0))

        # ---- respaldos
        backup_card = Card(body, padding=18)
        backup_card.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        card_title(backup_card.inner, "Respaldos y exportación",
                   "Guarda una copia de seguridad o lleva tus datos a una hoja de cálculo"
                   ).pack(fill="x")
        tk.Label(backup_card.inner, text=f"Base de datos: {self.db.path}",
                 bg=theme.CARD, fg=theme.MUTED, font=font(8), anchor="w",
                 wraplength=760, justify="left").pack(fill="x", pady=(10, 10))
        buttons = tk.Frame(backup_card.inner, bg=theme.CARD)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Crear respaldo (.json)", style="Secondary.TButton",
                   command=self._backup).pack(side="left")
        ttk.Button(buttons, text="Restaurar respaldo", style="Secondary.TButton",
                   command=self._restore).pack(side="left", padx=8)
        ttk.Button(buttons, text="Exportar todo (.csv)", style="Secondary.TButton",
                   command=self._export_all).pack(side="left")
        ttk.Button(buttons, text="Abrir carpeta", style="Ghost.TButton",
                   command=self._open_folder).pack(side="left", padx=6)

        # ---- datos de ejemplo
        demo_card = Card(body, padding=18)
        demo_card.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        card_title(demo_card.inner, "Datos de ejemplo",
                   "Genera seis meses de movimientos para explorar la aplicación"
                   ).pack(fill="x")
        tk.Label(demo_card.inner,
                 text="Se agregan a tus datos actuales; no borra nada. Puedes eliminarlos "
                      "después con «Borrar todos los datos».",
                 bg=theme.CARD, fg=theme.MUTED, font=font(9), anchor="w",
                 wraplength=760, justify="left").pack(fill="x", pady=(10, 10))
        ttk.Button(demo_card.inner, text="Cargar datos de ejemplo",
                   style="Secondary.TButton",
                   command=self.app.load_demo_data).pack(anchor="w")

        # ---- zona de riesgo
        danger_card = Card(body, padding=18)
        danger_card.grid(row=5, column=0, sticky="ew", pady=(14, 0))
        card_title(danger_card.inner, "Zona de riesgo",
                   "Estas acciones no se pueden deshacer").pack(fill="x")
        tk.Label(danger_card.inner,
                 text="Se eliminarán todos los movimientos, presupuestos, categorías, "
                      "cuentas, reglas automáticas y movimientos recurrentes, y se "
                      "restaurarán los valores iniciales. Crea un respaldo antes.",
                 bg=theme.CARD, fg=theme.MUTED, font=font(9), anchor="w",
                 wraplength=760, justify="left").pack(fill="x", pady=(10, 10))
        ttk.Button(danger_card.inner, text="Borrar todos los datos",
                   style="DangerSolid.TButton", command=self._wipe).pack(anchor="w")

        # ---- acerca de
        about = Card(body, padding=18)
        about.grid(row=6, column=0, sticky="ew", pady=(14, 0))
        card_title(about.inner, "Acerca de", f"Finanzas {__version__}").pack(fill="x")
        tk.Label(
            about.inner,
            text="Aplicación de finanzas personales hecha con Python y Tkinter. "
                 "Tus datos viven únicamente en tu equipo, en una base de datos SQLite.\n\n"
                 "Atajos: Ctrl+N nuevo movimiento · Ctrl+F buscar · Ctrl+Z deshacer · "
                 "F5 actualizar · Supr eliminar seleccionado · Esc cerrar diálogos.",
            bg=theme.CARD, fg=theme.MUTED, font=font(9), anchor="w",
            justify="left", wraplength=760,
        ).pack(fill="x", pady=(10, 0))

    # ------------------------------------------------------------ acciones
    def _refresh_display_options(self):
        self.display_combo.configure(values=self.app.available_display_currencies())
        self.display_var.set(self.app.display_currency_code())
        if self.app.display_currency:
            self.display_hint.configure(
                text=f"{self.app.display_rate_text()} · los datos guardados no cambian."
            )
        elif len(self.app.available_display_currencies()) > 1:
            self.display_hint.configure(
                text="Elige una moneda con tasa para convertir los montos solo al mostrarlos."
            )
        else:
            self.display_hint.configure(
                text="Registra una tasa abajo para poder ver los montos en otra moneda."
            )

    def _change_display(self, _event=None):
        self.app.set_display_currency(self.display_var.get())
        self._refresh_display_options()

    def _change_theme(self, _event=None):
        mode = THEME_LABELS.get(self.theme_var.get(), "light")
        self.app.set_theme(mode)
        if theme.MODE != mode:
            # No se pudo cambiar (por ejemplo, hay un diálogo abierto).
            self.theme_var.set(THEME_VALUES.get(theme.MODE, "Claro"))

    def _change_number_format(self, _event=None):
        style = "es" if self.number_var.get() == NUMBER_LABELS["es"] else "en"
        self.db.set_setting("number_format", style)
        self.app.number_format = style
        self.app.refresh_current()
        self.app._refresh_display_controls()
        self.app.toast("Formato de números actualizado")

    def _save_currency(self):
        symbol = self.currency_var.get().strip()
        if not symbol or len(symbol) > 5:
            self.app.toast("Usa un símbolo de hasta 5 caracteres, por ejemplo $ o €", "error")
            return
        self.db.set_setting("currency", symbol)
        self.app.currency = symbol
        self.app.refresh_current()
        self.app._refresh_display_controls()
        self.app.update_sidebar()
        self.app.toast("Moneda actualizada")

    def _save_base(self):
        code = self.base_var.get().strip().upper()
        if code == self.app.base_currency:
            self.app.toast("Esa ya es la moneda base", "info")
            return
        if not code:
            self.app.toast("Escribe un código de moneda base, por ejemplo USD", "error")
            return
        if self.db.has_transactions() or self.db.fx_rates():
            if not ask_confirm(
                self, "Cambiar la moneda base",
                "Los montos existentes se interpretarán en la nueva moneda base. "
                "Las tasas de cambio guardadas para esa moneda se eliminarán. "
                "Revisa las tasas después del cambio. ¿Continuar?",
                confirm_text="Cambiar base", danger=False,
            ):
                return
        try:
            self.db.set_base_currency(code)
        except ValueError as exc:
            self.app.toast(str(exc), "error")
            return
        self.app.base_currency = self.db.base_currency()
        self.app.reload_all()
        self.app.toast(f"Moneda base: {self.app.base_currency}")

    def _refresh_rates(self):
        for item in self.rates_tree.get_children():
            self.rates_tree.delete(item)
        base = self.app.base_currency
        self.rates_tree.heading("rate", text=f"1 unidad = {base}", anchor="e")
        self.fx_hint.configure(
            text=f"1 unidad de la moneda extranjera = X unidades de {base}. "
                 "Se usa la tasa más reciente anterior o igual a la fecha del movimiento."
        )
        rows = self.db.fx_rates()
        for row in rows:
            rate = row["rate"]
            body = localize_number(f"{rate:,.6f}", self.app.number_format)
            body = body.rstrip("0").rstrip(".,") or "0"
            self.rates_tree.insert(
                "", "end", iid=f"{row['currency']}|{row['date']}",
                values=(row["currency"], _fmt_iso(row["date"]), body),
            )
        self._refresh_display_options()
        missing = self.db.missing_rates()
        if missing:
            self.fx_status.configure(
                text="Faltan tasas para: " + ", ".join(missing)
                     + ". Las cuentas de esas monedas se convierten 1:1 hasta que "
                       "registres una tasa.",
                fg=theme.AMBER,
            )
        elif not rows:
            self.fx_status.configure(
                text="Aún no hay tasas. Solo son necesarias si tienes cuentas en "
                     "monedas distintas a la base.",
                fg=theme.SUBTLE,
            )
        elif self.app.display_currency:
            self.fx_status.configure(
                text=f"Vista actual: montos convertidos a {self.app.display_currency} "
                     f"({self.app.display_rate_text()}). Los datos guardados no cambian.",
                fg=theme.MUTED,
            )
        elif not self.db.has_foreign_accounts():
            currencies = sorted({row["currency"] for row in rows})
            self.fx_status.configure(
                text=f"Tasas guardadas para {', '.join(currencies)}. Usa «Mostrar "
                     "montos en» o el selector «Ver en» de la cabecera para ver todos "
                     "tus datos convertidos, sin crear cuentas nuevas.",
                fg=theme.MUTED,
            )
        else:
            self.fx_status.configure(text="", fg=theme.SUBTLE)

    def _save_rate(self):
        currency = self.rate_currency_var.get().strip().upper()
        date_text = self.rate_date_var.get().strip() or dt.date.today().strftime("%d/%m/%Y")
        try:
            date = parse_date(date_text).isoformat()
            rate = _parse_rate(self.rate_value_var.get())
            self.db.set_fx_rate(currency, date, rate)
        except ValueError as exc:
            self.app.toast(str(exc), "error")
            return
        self.rate_currency_var.set(currency)
        self.rate_value_var.set("")
        self._refresh_rates()
        self.app._refresh_display_controls()
        self.app.refresh_current()
        self.app.update_sidebar()
        self.app.toast(f"Tasa guardada: 1 {currency} = {rate} {self.app.base_currency}")

    def _delete_rate(self):
        selection = self.rates_tree.selection()
        if not selection:
            self.app.toast("Selecciona una tasa para eliminarla", "info")
            return
        currency, date = selection[0].split("|", 1)
        if not ask_confirm(
            self, "Eliminar tipo de cambio",
            f"¿Eliminar la tasa de {currency} del {_fmt_iso(date)}?",
        ):
            return
        was_display = self.app.display_currency
        self.db.delete_fx_rate(currency, date)
        self.app.ensure_display_currency()
        self._refresh_rates()
        self.app._refresh_display_controls()
        self.app.refresh_current()
        self.app.update_sidebar()
        if was_display and not self.app.display_currency:
            self.app.toast(
                f"Tasa eliminada · montos de nuevo en {self.app.base_currency}"
            )
        else:
            self.app.toast("Tasa eliminada")

    def _backup(self):
        path = filedialog.asksaveasfilename(
            parent=self, title="Crear respaldo",
            defaultextension=".json", filetypes=[("Respaldo de Finanzas", "*.json")],
            initialfile=f"finanzas_respaldo_{dt.date.today():%Y%m%d}.json",
        )
        if not path:
            return
        try:
            self.db.backup_json(path)
        except OSError as exc:
            self.app.toast(f"No se pudo crear el respaldo: {exc}", "error")
            return
        self.app.toast("Respaldo creado correctamente")

    def _restore(self):
        path = filedialog.askopenfilename(
            parent=self, title="Restaurar respaldo",
            filetypes=[("Respaldo de Finanzas", "*.json"), ("Todos los archivos", "*.*")],
        )
        if not path:
            return
        if not ask_confirm(
            self, "Restaurar respaldo",
            "Se reemplazarán TODOS tus datos actuales por los del respaldo. "
            "¿Deseas continuar?",
            confirm_text="Restaurar",
        ):
            return
        try:
            self.db.restore_json(path)
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            self.app.toast(f"No se pudo restaurar: {exc}", "error")
            return
        self.app.reload_all()
        self.app.toast("Respaldo restaurado")

    def _export_all(self):
        path = filedialog.asksaveasfilename(
            parent=self, title="Exportar todos los movimientos",
            defaultextension=".csv", filetypes=[("Archivo CSV", "*.csv")],
            initialfile=f"movimientos_{dt.date.today():%Y%m%d}.csv",
        )
        if not path:
            return
        try:
            count = self.db.export_csv(path)
        except OSError as exc:
            self.app.toast(f"No se pudo exportar: {exc}", "error")
            return
        self.app.toast(f"{count} movimientos exportados")

    def _open_folder(self):
        folder = self.db.path.parent
        try:
            subprocess.Popen(["xdg-open", str(folder)])
        except OSError:
            self.app.toast(f"Carpeta de datos: {folder}", "info")

    def _wipe(self):
        if not ask_confirm(
            self, "Borrar todos los datos",
            "Se eliminarán todos los movimientos, presupuestos, categorías, cuentas, "
            "reglas y recurrentes. Esta acción no se puede deshacer. ¿Continuar?",
            confirm_text="Borrar todo",
        ):
            return
        self.db.wipe_data()
        self.app.reload_all()
        self.app.toast("Todos los datos fueron eliminados")


def _fmt_iso(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso or ""
