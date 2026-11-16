"""Widgets reutilizables: tarjetas, gráficas y contenedores."""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from . import theme
from .theme import font
from .utils import money, money_compact, truncate


# ---------------------------------------------------------------- básicos
class Card(tk.Frame):
    """Panel con borde sutil que toma el color del tema actual."""

    def __init__(self, parent, padding: int = 18, bg: str | None = None, **kwargs):
        bg = theme.CARD if bg is None else bg
        super().__init__(
            parent, bg=bg, highlightbackground=theme.BORDER,
            highlightcolor=theme.BORDER, highlightthickness=1, bd=0, **kwargs,
        )
        self._bg = bg
        self.inner = tk.Frame(self, bg=bg)
        self.inner.pack(fill="both", expand=True, padx=padding, pady=padding)


class StatCard(Card):
    def __init__(self, parent, title: str, value: str = "—", hint: str = "",
                 accent: str | None = None):
        super().__init__(parent, padding=16)
        accent = theme.PRIMARY if accent is None else accent
        top = tk.Frame(self.inner, bg=theme.CARD)
        top.pack(fill="x")
        dot = tk.Canvas(top, width=8, height=8, bg=theme.CARD, highlightthickness=0)
        dot.create_oval(1, 1, 7, 7, fill=accent, outline="")
        dot.pack(side="left", padx=(0, 7))
        tk.Label(
            top, text=title.upper(), bg=theme.CARD, fg=theme.MUTED, font=font(8, "bold"),
        ).pack(side="left")

        self.value_lbl = tk.Label(
            self.inner, text=value, bg=theme.CARD, fg=theme.TEXT,
            font=font(19, "bold"), anchor="w",
        )
        self.value_lbl.pack(fill="x", pady=(9, 1))
        self.hint_lbl = tk.Label(
            self.inner, text=hint, bg=theme.CARD, fg=theme.MUTED,
            font=font(9), anchor="w",
        )
        self.hint_lbl.pack(fill="x")

    def set_values(self, value: str, hint: str | None = None, color: str | None = None,
                   hint_color: str | None = None) -> None:
        self.value_lbl.configure(text=value, fg=theme.TEXT if color is None else color)
        if hint is not None:
            self.hint_lbl.configure(
                text=hint, fg=theme.MUTED if hint_color is None else hint_color
            )


class Badge(tk.Label):
    def __init__(self, parent, text: str, fg: str | None = None,
                 bg: str | None = None, size: int = 8):
        fg = theme.PRIMARY if fg is None else fg
        bg = theme.PRIMARY_SOFT if bg is None else bg
        super().__init__(parent, text=text, fg=fg, bg=bg, font=font(size, "bold"),
                         padx=8, pady=2)


class Divider(tk.Frame):
    def __init__(self, parent, bg: str | None = None, color: str | None = None):
        if bg is None:
            bg = theme.CARD
        if color is None:
            color = theme.BORDER
        super().__init__(parent, bg=color, height=1)


def card_title(parent, text: str, subtitle: str = "",
               bg: str | None = None) -> tk.Frame:
    bg = theme.CARD if bg is None else bg
    holder = tk.Frame(parent, bg=bg)
    tk.Label(holder, text=text, bg=bg, fg=theme.TEXT, font=font(11, "bold"),
             anchor="w").pack(fill="x")
    if subtitle:
        tk.Label(holder, text=subtitle, bg=bg, fg=theme.MUTED, font=font(9),
                 anchor="w").pack(fill="x", pady=(2, 0))
    return holder


def form_label(parent, text: str, bg: str | None = None) -> tk.Label:
    bg = theme.CARD if bg is None else bg
    return tk.Label(parent, text=text, bg=bg, fg=theme.MUTED, font=font(9, "bold"),
                    anchor="w")


# ---------------------------------------------------------------- scroll
class ScrollFrame(tk.Frame):
    """Contenedor desplazable; usa .body para agregar contenido."""

    def __init__(self, parent, bg: str | None = None):
        bg = theme.BG if bg is None else bg
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0,
                                yscrollincrement=20)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_body_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)

    def scroll_to_top(self):
        self.canvas.yview_moveto(0)


# ---------------------------------------------------------------- gráficas
def _round_rect(canvas: tk.Canvas, x1, y1, x2, y2, radius=4, **kwargs):
    radius = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


def _nice_max(value: float) -> float:
    if value <= 0:
        return 100.0
    magnitude = 10 ** math.floor(math.log10(value))
    for factor in (1, 2, 2.5, 5, 10):
        if value <= factor * magnitude:
            return factor * magnitude
    return 10 * magnitude


class BarChart(tk.Canvas):
    """Barras agrupadas de ingresos y egresos por mes."""

    def __init__(self, parent, height: int = 240, symbol: str = "$"):
        super().__init__(parent, bg=theme.CARD, highlightthickness=0, bd=0, height=height)
        self.data: list[dict] = []
        self.symbol = symbol
        self.style = "en"
        self.bind("<Configure>", lambda _e: self._draw())

    def set_data(self, data, symbol: str | None = None, style: str | None = None):
        self.data = data or []
        if symbol:
            self.symbol = symbol
        if style:
            self.style = style
        self._draw()

    def _draw(self):
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        if width < 80 or height < 80:
            return
        if not self.data:
            self.create_text(width / 2, height / 2, text="Sin datos todavía",
                             fill=theme.SUBTLE, font=font(10))
            return

        left, right, top, bottom = 56, 12, 30, 28
        plot_w = max(10, width - left - right)
        plot_h = max(10, height - top - bottom)
        peak = max([d["income"] for d in self.data] + [d["expense"] for d in self.data] + [1])
        top_value = _nice_max(peak)

        # cuadrícula
        for i in range(5):
            y = top + plot_h * i / 4
            self.create_line(left, y, width - right, y, fill=theme.GRID)
            self.create_text(left - 8, y,
                             text=money_compact(int(top_value * (4 - i) / 4), self.symbol,
                                                self.style),
                             anchor="e", fill=theme.SUBTLE, font=font(8))

        # leyenda
        legend_x = width - right - 158
        for offset, color, label in ((0, theme.GREEN, "Ingresos"), (78, theme.RED, "Egresos")):
            self.create_rectangle(legend_x + offset, 8, legend_x + offset + 8, 16,
                                  fill=color, outline="")
            self.create_text(legend_x + offset + 13, 12, text=label, anchor="w",
                             fill=theme.MUTED, font=font(8))

        group_w = plot_w / len(self.data)
        bar_w = max(4.0, min(16.0, group_w * 0.3))
        gap = 3
        base_y = top + plot_h
        for idx, item in enumerate(self.data):
            center = left + group_w * (idx + 0.5)
            for value, color, direction in ((item["income"], theme.GREEN, -1),
                                            (item["expense"], theme.RED, 1)):
                if value <= 0:
                    continue
                bar_h = max(2.0, plot_h * value / top_value)
                x1 = center - bar_w - gap / 2 if direction < 0 else center + gap / 2
                _round_rect(self, x1, base_y - bar_h, x1 + bar_w, base_y, 3,
                            fill=color, outline="")
            try:
                from .utils import MESES_CORTOS
                month = int(item["key"].split("-")[1])
                label = MESES_CORTOS[month - 1]
            except (KeyError, ValueError, IndexError):
                label = str(item.get("key", ""))
            self.create_text(center, base_y + 14, text=label, fill=theme.MUTED, font=font(8))


class DonutChart(tk.Canvas):
    def __init__(self, parent, size: int = 170, symbol: str = "$"):
        super().__init__(parent, width=size, height=size, bg=theme.CARD,
                         highlightthickness=0, bd=0)
        self._size = size
        self.symbol = symbol
        self.items: list[tuple[str, int, str]] = []
        self.center_value = ""
        self.center_sub = ""
        self.bind("<Configure>", lambda _e: self._draw())

    def set_data(self, items, center_value: str = "", center_sub: str = "",
                 symbol: str | None = None):
        self.items = items or []
        self.center_value = center_value
        self.center_sub = center_sub
        if symbol:
            self.symbol = symbol
        self._draw()

    def _draw(self):
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        if width < 40 or height < 40:
            return
        size = min(width, height)
        pad = max(8, size * 0.08)
        thickness = max(14, int(size * 0.14))
        box = (pad + thickness / 2, pad + thickness / 2,
               size - pad - thickness / 2, size - pad - thickness / 2)
        total = sum(v for _, v, _ in self.items)

        if total <= 0:
            self.create_arc(*box, start=0, extent=359.9, style=tk.ARC,
                            outline=theme.GRID, width=thickness)
            self.create_text(size / 2, size / 2 - 7, text="Sin datos",
                             fill=theme.SUBTLE, font=font(9))
            return

        angle = 90.0
        for _label, value, color in self.items:
            extent = -360.0 * value / total
            self.create_arc(*box, start=angle, extent=extent + (1.0 if extent < -1 else 0),
                            style=tk.ARC, outline=color, width=thickness)
            angle += extent

        if self.center_value:
            self.create_text(size / 2, size / 2 - 8, text=self.center_value,
                             fill=theme.TEXT, font=font(13, "bold"))
        if self.center_sub:
            self.create_text(size / 2, size / 2 + 13, text=self.center_sub,
                             fill=theme.MUTED, font=font(8))


class ProgressBar(tk.Canvas):
    def __init__(self, parent, height: int = 8, bg: str | None = None):
        bg = theme.CARD if bg is None else bg
        super().__init__(parent, height=height, bg=bg, highlightthickness=0, bd=0)
        self._bg = bg
        self._pct = 0.0
        self._color = theme.PRIMARY
        self.bind("<Configure>", lambda _e: self._draw())

    def set(self, pct_value: float, color: str | None = None):
        self._pct = max(0.0, min(1.0, pct_value / 100))
        self._color = theme.PRIMARY if color is None else color
        self._draw()

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 4 or height < 4:
            return
        _round_rect(self, 0, 0, width, height, height / 2, fill=theme.GRID, outline="")
        if self._pct > 0:
            fill_w = max(height, width * self._pct)
            _round_rect(self, 0, 0, fill_w, height, height / 2, fill=self._color, outline="")


class EmptyState(tk.Frame):
    def __init__(self, parent, title: str, subtitle: str = "", glyph: str = "◎",
                 action=None, action_text: str = "", bg: str | None = None,
                 secondary=None, secondary_text: str = ""):
        bg = theme.CARD if bg is None else bg
        super().__init__(parent, bg=bg)
        art = tk.Canvas(self, width=64, height=64, bg=bg, highlightthickness=0)
        art.create_oval(2, 2, 62, 62, fill=theme.PRIMARY_SOFT, outline="")
        art.create_text(32, 32, text=glyph, fill=theme.PRIMARY, font=font(22, "bold"))
        art.pack(pady=(6, 12))
        tk.Label(self, text=title, bg=bg, fg=theme.TEXT, font=font(12, "bold")).pack()
        if subtitle:
            tk.Label(self, text=subtitle, bg=bg, fg=theme.MUTED, font=font(9),
                     wraplength=380, justify="center").pack(pady=(4, 14))
        if action or secondary:
            row = tk.Frame(self, bg=bg)
            row.pack(pady=(4, 6))
            if action:
                ttk.Button(row, text=action_text or "Continuar", style="Primary.TButton",
                           command=action).pack(side="left", padx=4)
            if secondary:
                ttk.Button(row, text=secondary_text or "Opciones", style="Secondary.TButton",
                           command=secondary).pack(side="left", padx=4)


def legend_row(parent, color: str, label: str, value: str, bg: str | None = None,
               max_label: int = 18) -> tk.Frame:
    bg = theme.CARD if bg is None else bg
    row = tk.Frame(parent, bg=bg)
    dot = tk.Canvas(row, width=10, height=10, bg=bg, highlightthickness=0)
    dot.create_oval(2, 2, 9, 9, fill=color, outline="")
    dot.pack(side="left", padx=(0, 7))
    tk.Label(row, text=truncate(label, max_label), bg=bg, fg=theme.MUTED,
             font=font(9), anchor="w").pack(side="left")
    tk.Label(row, text=value, bg=bg, fg=theme.TEXT, font=font(9, "bold"),
             anchor="e").pack(side="right")
    return row


def kv_line(parent, label: str, value: str, bg: str | None = None,
            value_color: str | None = None) -> tk.Frame:
    bg = theme.CARD if bg is None else bg
    value_color = theme.TEXT if value_color is None else value_color
    row = tk.Frame(parent, bg=bg)
    tk.Label(row, text=label, bg=bg, fg=theme.MUTED, font=font(9),
             anchor="w").pack(side="left")
    tk.Label(row, text=value, bg=bg, fg=value_color, font=font(9, "bold"),
             anchor="e").pack(side="right")
    return row
