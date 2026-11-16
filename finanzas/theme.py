"""Paleta, tipografías y estilos ttk de la aplicación.

La paleta está centralizada aquí para poder alternar entre modo claro y oscuro.
Los widgets se crean con los valores actuales del módulo; al cambiar de tema la
App reconstruye la interfaz para que todos tomen los colores nuevos.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# ---------------------------------------------------------------- paletas
LIGHT = {
    "BG": "#f3f4f6",
    "CARD": "#ffffff",
    "CARD_SOFT": "#f9fafb",
    "BORDER": "#e5e7eb",
    "BORDER_STRONG": "#d1d5db",
    "TEXT": "#111827",
    "MUTED": "#6b7280",
    "SUBTLE": "#9ca3af",
    "PRIMARY": "#4f46e5",
    "PRIMARY_DARK": "#4338ca",
    "PRIMARY_SOFT": "#eef2ff",
    "GREEN": "#059669",
    "GREEN_SOFT": "#ecfdf5",
    "GREEN_DARK": "#065f46",
    "RED": "#dc2626",
    "RED_SOFT": "#fef2f2",
    "RED_DARK": "#991b1b",
    "RED_HOVER": "#b91c1c",
    "RED_SOFT_HOVER": "#fee2e2",
    "AMBER": "#d97706",
    "AMBER_SOFT": "#fffbeb",
    "BLUE": "#2563eb",
    "BLUE_SOFT": "#eff6ff",
    "BLUE_DARK": "#1e40af",
    "PURPLE": "#7c3aed",
    "PURPLE_SOFT": "#f5f3ff",
    "SIDEBAR": "#0f172a",
    "SIDEBAR_HOVER": "#1e293b",
    "SIDEBAR_TEXT": "#cbd5e1",
    "SIDEBAR_MUTED": "#94a3b8",
    "SIDEBAR_CARD": "#1e293b",
    "SIDEBAR_FG": "#ffffff",
    "GRID": "#eef0f3",
    "TOAST_BG": "#111827",
    "TOAST_TEXT": "#f9fafb",
    "TOAST_ACTION": "#a5b4fc",
    "ON_PRIMARY": "#ffffff",
}

DARK = {
    "BG": "#0b1220",
    "CARD": "#111827",
    "CARD_SOFT": "#1a2334",
    "BORDER": "#243044",
    "BORDER_STRONG": "#334155",
    "TEXT": "#e5e7eb",
    "MUTED": "#a3b1c6",
    "SUBTLE": "#7f8ea3",
    "PRIMARY": "#6366f1",
    "PRIMARY_DARK": "#a5b4fc",
    "PRIMARY_SOFT": "#1e1b4b",
    "GREEN": "#34d399",
    "GREEN_SOFT": "#052e2b",
    "GREEN_DARK": "#a7f3d0",
    "RED": "#f87171",
    "RED_SOFT": "#3f1d1d",
    "RED_DARK": "#fecaca",
    "RED_HOVER": "#ef4444",
    "RED_SOFT_HOVER": "#4c1d1d",
    "AMBER": "#fbbf24",
    "AMBER_SOFT": "#3a2c08",
    "BLUE": "#60a5fa",
    "BLUE_SOFT": "#172554",
    "BLUE_DARK": "#bfdbfe",
    "PURPLE": "#c084fc",
    "PURPLE_SOFT": "#2e1065",
    "SIDEBAR": "#070c16",
    "SIDEBAR_HOVER": "#111a2b",
    "SIDEBAR_TEXT": "#d7dee9",
    "SIDEBAR_MUTED": "#94a3b8",
    "SIDEBAR_CARD": "#111a2b",
    "SIDEBAR_FG": "#ffffff",
    "GRID": "#1f2a3c",
    "TOAST_BG": "#1f2937",
    "TOAST_TEXT": "#f9fafb",
    "TOAST_ACTION": "#a5b4fc",
    "ON_PRIMARY": "#ffffff",
}

PALETTES = {"light": LIGHT, "dark": DARK}
MODE = "light"

CATEGORY_COLORS = [
    "#ef4444", "#f97316", "#f59e0b", "#84cc16", "#22c55e", "#10b981",
    "#14b8a6", "#06b6d4", "#0ea5e9", "#6366f1", "#a855f7", "#ec4899",
    "#64748b", "#94a3b8",
]

FONT_FAMILY = "DejaVu Sans"
_FONT_CANDIDATES = ["Inter", "Segoe UI", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans"]


def _rebuild_account_kinds() -> None:
    global ACCOUNT_KINDS
    ACCOUNT_KINDS = {
        "efectivo": ("Efectivo", GREEN, GREEN_SOFT),
        "banco": ("Banco", PRIMARY, PRIMARY_SOFT),
        "tarjeta": ("Tarjeta", AMBER, AMBER_SOFT),
        "ahorro": ("Ahorro", BLUE, BLUE_SOFT),
        "inversion": ("Inversión", PURPLE, PURPLE_SOFT),
    }


def set_mode(mode: str) -> str:
    """Activa ``light`` o ``dark`` y actualiza los colores del módulo."""
    global MODE
    mode = "dark" if str(mode).lower() == "dark" else "light"
    MODE = mode
    palette = PALETTES[mode]
    globals().update(palette)
    _rebuild_account_kinds()
    return mode


def toggle_mode() -> str:
    return set_mode("light" if MODE == "dark" else "dark")


# Inicializa los nombres globales de la paleta clara.
set_mode("light")


def font(size: int = 10, weight: str = "normal", slant: str = "roman") -> tuple:
    return (FONT_FAMILY, size, weight, slant)


def _pick_family(root) -> str:
    available = set(tkfont.families(root))
    for name in _FONT_CANDIDATES:
        if name in available:
            return name
    return "TkDefaultFont"


def apply_theme(root: tk.Misc) -> None:
    global FONT_FAMILY
    FONT_FAMILY = _pick_family(root)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=BG)
    root.option_add("*Font", font(10))
    root.option_add("*TCombobox*Listbox.background", CARD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", PRIMARY)
    root.option_add("*TCombobox*Listbox.selectForeground", ON_PRIMARY)
    root.option_add("*TCombobox*Listbox.font", font(10))

    style.configure(".", background=BG, foreground=TEXT, font=font(10))

    # ---- botones
    style.configure(
        "Primary.TButton", background=PRIMARY, foreground=ON_PRIMARY, borderwidth=0,
        focusthickness=0, padding=(14, 8), relief="flat", font=font(9, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[("active", PRIMARY_DARK), ("pressed", PRIMARY_DARK),
                    ("disabled", BORDER_STRONG)],
        foreground=[("disabled", MUTED)],
    )
    style.configure(
        "Secondary.TButton", background=CARD_SOFT, foreground=TEXT, borderwidth=1,
        bordercolor=BORDER_STRONG, focusthickness=0, padding=(12, 7), relief="flat",
        font=font(9, "bold"),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", BG), ("pressed", BORDER)],
        bordercolor=[("active", BORDER_STRONG)],
    )
    style.configure(
        "Ghost.TButton", background=CARD, foreground=MUTED, borderwidth=0,
        focusthickness=0, padding=(9, 6), relief="flat", font=font(9),
    )
    style.map(
        "Ghost.TButton",
        background=[("active", CARD_SOFT)],
        foreground=[("active", TEXT)],
    )
    style.configure(
        "Danger.TButton", background=RED_SOFT, foreground=RED, borderwidth=0,
        focusthickness=0, padding=(12, 7), relief="flat", font=font(9, "bold"),
    )
    style.map("Danger.TButton", background=[("active", RED_SOFT_HOVER)])
    style.configure(
        "DangerSolid.TButton", background=RED, foreground=ON_PRIMARY, borderwidth=0,
        focusthickness=0, padding=(14, 8), relief="flat", font=font(9, "bold"),
    )
    style.map("DangerSolid.TButton", background=[("active", RED_HOVER)])
    style.configure(
        "DangerLink.TButton", background=CARD, foreground=RED, borderwidth=0,
        focusthickness=0, padding=(9, 6), relief="flat", font=font(9),
    )
    style.map(
        "DangerLink.TButton",
        background=[("active", RED_SOFT)],
        foreground=[("active", RED)],
    )
    style.configure(
        "Link.TButton", background=CARD, foreground=PRIMARY_DARK, borderwidth=0,
        focusthickness=0, padding=(4, 2), relief="flat", font=font(9, "bold"),
    )
    style.map(
        "Link.TButton",
        foreground=[("active", TEXT)],
        background=[("active", CARD_SOFT)],
    )

    style.configure(
        "Nav.TButton", background=SIDEBAR, foreground=SIDEBAR_TEXT, borderwidth=0,
        focusthickness=0, padding=(18, 10), relief="flat", anchor="w", font=font(10),
    )
    style.map(
        "Nav.TButton",
        background=[("active", SIDEBAR_HOVER)],
        foreground=[("active", ON_PRIMARY)],
    )
    style.configure(
        "NavActive.TButton", background=PRIMARY, foreground=ON_PRIMARY, borderwidth=0,
        focusthickness=0, padding=(18, 10), relief="flat", anchor="w", font=font(10, "bold"),
    )
    style.map(
        "NavActive.TButton",
        background=[("active", PRIMARY), ("pressed", PRIMARY)],
        foreground=[("active", ON_PRIMARY)],
    )

    # ---- entradas
    style.configure(
        "TEntry", fieldbackground=CARD, foreground=TEXT, insertcolor=TEXT,
        bordercolor=BORDER_STRONG, lightcolor=CARD, darkcolor=CARD,
        padding=(8, 7), relief="flat", font=font(10),
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", PRIMARY)],
        lightcolor=[("focus", PRIMARY)],
        darkcolor=[("focus", PRIMARY)],
    )
    style.configure(
        "Big.TEntry", fieldbackground=CARD, foreground=TEXT, insertcolor=TEXT,
        bordercolor=BORDER_STRONG, lightcolor=CARD, darkcolor=CARD,
        padding=(10, 9), relief="flat", font=font(16, "bold"),
    )
    style.map(
        "Big.TEntry",
        bordercolor=[("focus", PRIMARY)],
        lightcolor=[("focus", PRIMARY)],
        darkcolor=[("focus", PRIMARY)],
    )
    style.configure(
        "TSpinbox", fieldbackground=CARD, background=CARD, foreground=TEXT,
        insertcolor=TEXT, arrowcolor=MUTED, bordercolor=BORDER_STRONG,
        lightcolor=CARD, darkcolor=CARD, padding=(8, 7), relief="flat",
        font=font(10),
    )
    style.map(
        "TSpinbox",
        fieldbackground=[("readonly", CARD), ("disabled", CARD_SOFT)],
        foreground=[("disabled", SUBTLE)],
        bordercolor=[("focus", PRIMARY)],
        lightcolor=[("focus", PRIMARY)],
        darkcolor=[("focus", PRIMARY)],
    )
    style.configure(
        "TCombobox", fieldbackground=CARD, background=CARD, foreground=TEXT,
        arrowcolor=MUTED, bordercolor=BORDER_STRONG, lightcolor=CARD,
        darkcolor=CARD, padding=(7, 6), relief="flat", font=font(10),
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", CARD), ("disabled", CARD_SOFT)],
        foreground=[("readonly", TEXT), ("disabled", SUBTLE)],
        bordercolor=[("focus", PRIMARY), ("hover", BORDER_STRONG)],
        selectbackground=[("readonly", CARD)],
        selectforeground=[("readonly", TEXT)],
    )
    style.configure("TCheckbutton", background=CARD, foreground=MUTED, font=font(9))
    style.map("TCheckbutton", background=[("active", CARD)], foreground=[("active", TEXT)])

    # ---- tablas
    style.configure(
        "Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
        rowheight=34, borderwidth=0, font=font(10),
    )
    style.map(
        "Treeview",
        background=[("selected", PRIMARY_SOFT)],
        foreground=[("selected", TEXT)],
    )
    style.configure(
        "Treeview.Heading", background=CARD_SOFT, foreground=MUTED,
        font=font(9, "bold"), relief="flat", padding=(10, 9), borderwidth=0,
    )
    style.map("Treeview.Heading", background=[("active", BG)])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    # ---- barras de desplazamiento
    style.configure(
        "Vertical.TScrollbar", background=BORDER_STRONG, troughcolor=CARD,
        bordercolor=CARD, arrowcolor=MUTED, relief="flat", arrowsize=12,
    )
    style.map("Vertical.TScrollbar", background=[("active", SUBTLE)])
