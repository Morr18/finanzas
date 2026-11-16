"""Punto de entrada: python3 -m finanzas"""
from __future__ import annotations

import sys
import traceback
from tkinter import messagebox


def main() -> int:
    try:
        from .app import App

        app = App()
        app.mainloop()
        return 0
    except Exception:
        details = traceback.format_exc()
        try:
            messagebox.showerror(
                "Finanzas",
                "No se pudo iniciar la aplicación.\n\n" + details[-1200:],
            )
        except Exception:
            print(details, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
