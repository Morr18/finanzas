"""Capa de datos sobre SQLite. Todos los montos se guardan en centavos."""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import json
import os
import random
import re
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from .utils import (
    FREQUENCY_LABELS, localize_number, month_bounds, month_key,
    next_recurring_date, parse_search_query, recent_month_keys,
    iter_recurring_dates,
)

DEFAULT_CATEGORIES = {
    "ingreso": [
        ("Salario", "#10b981"), ("Freelance", "#0ea5e9"), ("Inversiones", "#8b5cf6"),
        ("Ventas", "#f59e0b"), ("Otros ingresos", "#64748b"),
    ],
    "egreso": [
        ("Alimentación", "#ef4444"), ("Vivienda", "#f97316"), ("Transporte", "#eab308"),
        ("Servicios", "#06b6d4"), ("Salud", "#ec4899"), ("Educación", "#6366f1"),
        ("Ocio", "#a855f7"), ("Compras", "#14b8a6"), ("Ahorro e inversión", "#22c55e"),
        ("Impuestos", "#64748b"), ("Otros gastos", "#94a3b8"),
    ],
}

DEFAULT_ACCOUNTS = [
    ("Efectivo", "efectivo", 0, "#10b981"),
    ("Cuenta bancaria", "banco", 0, "#6366f1"),
    ("Ahorros", "ahorro", 0, "#0ea5e9"),
]

TYPE_LABEL = {"ingreso": "Ingreso", "egreso": "Egreso", "transferencia": "Transferencia"}
_KEEP = object()


def default_db_path() -> Path:
    override = os.environ.get("FINANZAS_DB")
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "finanzas" / "finanzas.db"


def normalize_currency(code: str | None) -> str:
    """Código ISO simple; vacío significa ''moneda base''."""
    value = (code or "").strip().upper()
    if value and not re.fullmatch(r"[A-Z]{3,5}", value):
        raise ValueError("Usa un código de moneda de 3 a 5 letras, por ejemplo USD.")
    return value


def _round_div(value: int, divisor: int) -> int:
    """División entera con redondeo half-up, conservando el signo."""
    sign = -1 if value < 0 else 1
    value = abs(int(value))
    quotient, remainder = divmod(value, int(divisor))
    if remainder * 2 >= int(divisor):
        quotient += 1
    return sign * quotient


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL COLLATE NOCASE UNIQUE,
    kind            TEXT NOT NULL DEFAULT 'efectivo',
    initial_balance INTEGER NOT NULL DEFAULT 0,
    color           TEXT NOT NULL DEFAULT '#6366f1',
    currency        TEXT NOT NULL DEFAULT '',
    archived        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS categories (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL COLLATE NOCASE,
    kind     TEXT NOT NULL CHECK (kind IN ('ingreso', 'egreso')),
    color    TEXT NOT NULL DEFAULT '#6366f1',
    archived INTEGER NOT NULL DEFAULT 0,
    UNIQUE (name, kind)
);
CREATE TABLE IF NOT EXISTS recurring (
    id                  INTEGER PRIMARY KEY,
    description         TEXT NOT NULL DEFAULT '',
    kind                TEXT NOT NULL CHECK (kind IN ('ingreso', 'egreso', 'transferencia')),
    amount              INTEGER NOT NULL CHECK (amount > 0),
    category_id         INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    account_id          INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    transfer_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    frequency           TEXT NOT NULL CHECK (frequency IN ('mensual', 'quincenal', 'semanal', 'anual')),
    day                 INTEGER NOT NULL DEFAULT 1,
    month               INTEGER,
    start_date          TEXT NOT NULL,
    last_run            TEXT,
    active              INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rules (
    id          INTEGER PRIMARY KEY,
    match_text  TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    account_id  INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fx_rates (
    currency    TEXT NOT NULL,
    date        TEXT NOT NULL,
    rate_micros INTEGER NOT NULL CHECK (rate_micros > 0),
    PRIMARY KEY (currency, date)
);
CREATE TABLE IF NOT EXISTS transactions (
    id                  INTEGER PRIMARY KEY,
    date                TEXT NOT NULL,
    kind                TEXT NOT NULL CHECK (kind IN ('ingreso', 'egreso', 'transferencia')),
    amount              INTEGER NOT NULL CHECK (amount > 0),
    transfer_amount     INTEGER,
    category_id         INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    account_id          INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    transfer_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    recurring_id        INTEGER REFERENCES recurring(id) ON DELETE SET NULL,
    description         TEXT NOT NULL DEFAULT '',
    notes               TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions (date);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions (category_id);
CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions (account_id);
CREATE TABLE IF NOT EXISTS budgets (
    category_id INTEGER PRIMARY KEY REFERENCES categories(id) ON DELETE CASCADE,
    amount      INTEGER NOT NULL DEFAULT 0
);
"""

POST_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_tx_recurring ON transactions (recurring_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tx_recurring_date
    ON transactions (recurring_id, date) WHERE recurring_id IS NOT NULL;
"""

# Se ordena por el texto que ve el usuario, incluidas las filas de transferencia.
SORT_COLUMNS = {
    "fecha": "t.date",
    "tipo": "t.kind",
    "descripcion": (
        "CASE WHEN TRIM(COALESCE(t.description, '')) <> '' THEN t.description "
        "WHEN t.kind = 'transferencia' THEN 'Entre cuentas' "
        "ELSE COALESCE(c.name, 'Sin categoría') END"
    ),
    "categoria": (
        "CASE WHEN t.kind = 'transferencia' THEN 'Transferencia' "
        "ELSE COALESCE(c.name, 'Sin categoría') END"
    ),
    "cuenta": (
        "CASE WHEN t.kind = 'transferencia' "
        "THEN COALESCE(a.name, '') || ' → ' || COALESCE(d.name, '') "
        "ELSE COALESCE(a.name, '') END"
    ),
    "monto": "t.amount",
}
TEXT_SORTS = {"descripcion", "categoria", "cuenta"}

TX_SELECT = """
SELECT t.*, c.name AS category_name, c.color AS category_color,
       a.name AS account_name, a.currency AS account_currency,
       d.name AS transfer_account_name, d.currency AS transfer_currency
FROM transactions t
LEFT JOIN categories c ON c.id = t.category_id
LEFT JOIN accounts a ON a.id = t.account_id
LEFT JOIN accounts d ON d.id = t.transfer_account_id
"""

TX_FROM = """
FROM transactions t
LEFT JOIN categories c ON c.id = t.category_id
LEFT JOIN accounts a ON a.id = t.account_id
LEFT JOIN accounts d ON d.id = t.transfer_account_id
"""


def _base_amount_sql(tx: str = "t", acc: str = "a") -> str:
    """Expresión SQL que convierte el monto a la moneda base según la fecha."""
    return (
        f"CAST(({tx}.amount * COALESCE(("
        f"SELECT r.rate_micros FROM fx_rates r "
        f"WHERE r.currency = {acc}.currency AND r.date <= {tx}.date "
        f"ORDER BY r.date DESC LIMIT 1), 1000000) + 500000) / 1000000 AS INTEGER)"
    )


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.executescript(POST_SCHEMA)
        self.conn.commit()
        self._seed_defaults()

    # ------------------------------------------------------------ base
    def close(self) -> None:
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    def _migrate(self) -> None:
        """Añade columnas a bases creadas con versiones anteriores."""
        def columns(table: str) -> set[str]:
            return {row["name"] for row in self.conn.execute(f"PRAGMA table_info({table})")}

        account_cols = columns("accounts")
        if "currency" not in account_cols:
            self.conn.execute(
                "ALTER TABLE accounts ADD COLUMN currency TEXT NOT NULL DEFAULT ''"
            )
        tx_cols = columns("transactions")
        if "transfer_amount" not in tx_cols:
            self.conn.execute("ALTER TABLE transactions ADD COLUMN transfer_amount INTEGER")
        if "recurring_id" not in tx_cols:
            self.conn.execute(
                "ALTER TABLE transactions ADD COLUMN recurring_id INTEGER"
                " REFERENCES recurring(id) ON DELETE SET NULL"
            )
        self.conn.execute("PRAGMA user_version = 2")

    def _seed_defaults(self) -> None:
        now = dt.datetime.now().isoformat(timespec="seconds")
        cur = self.conn.execute("SELECT COUNT(*) FROM categories")
        if cur.fetchone()[0] == 0:
            for kind, items in DEFAULT_CATEGORIES.items():
                for name, color in items:
                    self.conn.execute(
                        "INSERT INTO categories (name, kind, color, archived) VALUES (?,?,?,0)",
                        (name, kind, color),
                    )
        cur = self.conn.execute("SELECT COUNT(*) FROM accounts")
        if cur.fetchone()[0] == 0:
            for name, kind, initial, color in DEFAULT_ACCOUNTS:
                self.conn.execute(
                    "INSERT INTO accounts (name, kind, initial_balance, color, currency,"
                    " created_at) VALUES (?,?,?,?,?,?)",
                    (name, kind, initial, color, "", now),
                )
        for key, value in (
            ("currency", "$"), ("onboarding_done", "0"),
            ("base_currency", "USD"), ("theme", "light"), ("number_format", "en"),
        ):
            self.conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)", (key, value)
            )
        self.conn.commit()

    # ------------------------------------------------------------ ajustes
    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?,?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    def base_currency(self) -> str:
        return (self.get_setting("base_currency", "USD") or "USD").upper()

    def set_base_currency(self, code: str) -> None:
        code = normalize_currency(code)
        if not code:
            raise ValueError("Escribe un código de moneda base, por ejemplo USD.")
        if code == self.base_currency():
            return
        # Una tasa para la moneda base no tiene sentido: se elimina al cambiarla.
        self.conn.execute("DELETE FROM fx_rates WHERE currency = ?", (code,))
        self.set_setting("base_currency", code)

    def has_foreign_accounts(self) -> bool:
        base = self.base_currency()
        row = self.conn.execute(
            "SELECT EXISTS(SELECT 1 FROM accounts WHERE archived = 0"
            " AND currency <> '' AND currency <> ?)",
            (base,),
        ).fetchone()
        return bool(row[0])

    def missing_rates(self) -> list[str]:
        base = self.base_currency()
        rows = self.conn.execute(
            "SELECT DISTINCT currency FROM accounts WHERE archived = 0"
            " AND currency <> '' AND currency <> ?"
            " AND currency NOT IN (SELECT currency FROM fx_rates)",
            (base,),
        )
        return [r["currency"] for r in rows]

    # ------------------------------------------------------------ monedas
    def currencies_with_rates(self) -> list[str]:
        """Monedas extranjeras que tienen al menos una tasa registrada."""
        rows = self.conn.execute(
            "SELECT DISTINCT currency FROM fx_rates ORDER BY currency"
        )
        return [r["currency"] for r in rows if r["currency"]]

    def fx_rates(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM fx_rates ORDER BY currency, date DESC"
        )
        return [
            {
                "currency": r["currency"], "date": r["date"],
                "rate_micros": int(r["rate_micros"]),
                "rate": int(r["rate_micros"]) / 1_000_000,
            }
            for r in rows
        ]

    def set_fx_rate(self, currency: str, date: str, rate) -> None:
        code = normalize_currency(currency)
        if not code:
            raise ValueError("Escribe el código de la moneda extranjera.")
        if code == self.base_currency():
            raise ValueError("Esa es la moneda base; no necesita tipo de cambio.")
        try:
            dt.date.fromisoformat(date)
        except ValueError:
            raise ValueError("La fecha del tipo de cambio no es válida.")
        value = Decimal(str(rate))
        if value <= 0:
            raise ValueError("El tipo de cambio debe ser mayor que cero.")
        micros = int((value * 1_000_000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        self.conn.execute(
            "INSERT INTO fx_rates (currency, date, rate_micros) VALUES (?,?,?)"
            " ON CONFLICT(currency, date) DO UPDATE SET rate_micros = excluded.rate_micros",
            (code, date, micros),
        )
        self.conn.commit()

    def delete_fx_rate(self, currency: str, date: str) -> None:
        self.conn.execute(
            "DELETE FROM fx_rates WHERE currency = ? AND date = ?", (currency, date)
        )
        self.conn.commit()

    def fx_rate_micros(self, currency: str, date: str) -> int:
        code = (currency or "").strip().upper()
        if not code:
            return 1_000_000
        row = self.conn.execute(
            "SELECT rate_micros FROM fx_rates WHERE currency = ? AND date <= ?"
            " ORDER BY date DESC LIMIT 1",
            (code, date),
        ).fetchone()
        if row is None:
            row = self.conn.execute(
                "SELECT rate_micros FROM fx_rates WHERE currency = ?"
                " ORDER BY date DESC LIMIT 1",
                (code,),
            ).fetchone()
        return int(row["rate_micros"]) if row else 1_000_000

    def to_base(self, cents: int, currency: str, date: str) -> int:
        if not (currency or "").strip():
            return int(cents)
        return _round_div(int(cents) * self.fx_rate_micros(currency, date), 1_000_000)

    def from_base(self, cents: int, currency: str, date: str) -> int:
        if not (currency or "").strip():
            return int(cents)
        rate = self.fx_rate_micros(currency, date)
        return _round_div(int(cents) * 1_000_000, rate) if rate else int(cents)

    def convert_between(self, cents: int, from_currency: str, to_currency: str,
                        date: str) -> int:
        source = (from_currency or "").strip().upper()
        target = (to_currency or "").strip().upper()
        if source == target:
            return int(cents)
        base = self.to_base(cents, source, date)
        return self.from_base(base, target, date)

    def _transfer_amount(self, amount: int, account_id, transfer_account_id,
                         date: str) -> int | None:
        if not account_id or not transfer_account_id:
            return None
        source = self.get_account(account_id)
        target = self.get_account(transfer_account_id)
        if not source or not target:
            return None
        if (source["currency"] or "").upper() == (target["currency"] or "").upper():
            return None
        return self.convert_between(
            amount, source["currency"], target["currency"], date
        )

    # ------------------------------------------------------------ cuentas
    def accounts(self, include_archived: bool = False) -> list[dict]:
        sql = "SELECT * FROM accounts"
        if not include_archived:
            sql += " WHERE archived = 0"
        sql += " ORDER BY name COLLATE NOCASE"
        return [dict(r) for r in self.conn.execute(sql)]

    def account_balances(self) -> list[dict]:
        sql = """
        SELECT a.id, a.name, a.kind, a.color, a.initial_balance, a.archived, a.currency,
               a.initial_balance
               + COALESCE((SELECT SUM(amount) FROM transactions t
                           WHERE t.kind = 'ingreso' AND t.account_id = a.id), 0)
               - COALESCE((SELECT SUM(amount) FROM transactions t
                           WHERE t.kind = 'egreso' AND t.account_id = a.id), 0)
               - COALESCE((SELECT SUM(amount) FROM transactions t
                           WHERE t.kind = 'transferencia' AND t.account_id = a.id), 0)
               + COALESCE((SELECT SUM(COALESCE(t.transfer_amount, t.amount))
                           FROM transactions t
                           WHERE t.kind = 'transferencia'
                           AND t.transfer_account_id = a.id), 0)
               AS balance
        FROM accounts a
        WHERE a.archived = 0
        ORDER BY a.name COLLATE NOCASE
        """
        rows = [dict(r) for r in self.conn.execute(sql)]
        today = dt.date.today().isoformat()
        for row in rows:
            row["base_balance"] = self.to_base(
                row["balance"], row.get("currency", ""), today
            )
        return rows

    def total_balance(self) -> int:
        return sum(a["base_balance"] for a in self.account_balances())

    def get_account(self, account_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return dict(row) if row else None

    def add_account(self, name: str, kind: str, initial_balance: int, color: str,
                    currency: str = "") -> int:
        now = dt.datetime.now().isoformat(timespec="seconds")
        code = normalize_currency(currency)
        if code == self.base_currency():
            code = ""
        cur = self.conn.execute(
            "INSERT INTO accounts (name, kind, initial_balance, color, currency, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (name.strip(), kind, int(initial_balance), color, code, now),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_account(self, account_id: int, name: str, kind: str,
                       initial_balance: int, color: str, currency: str = "") -> None:
        code = normalize_currency(currency)
        if code == self.base_currency():
            code = ""
        self.conn.execute(
            "UPDATE accounts SET name = ?, kind = ?, initial_balance = ?, color = ?,"
            " currency = ? WHERE id = ?",
            (name.strip(), kind, int(initial_balance), color, code, account_id),
        )
        self.conn.commit()

    def account_usage(self, account_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE account_id = ? OR transfer_account_id = ?",
            (account_id, account_id),
        ).fetchone()
        return int(row[0])

    def delete_account(self, account_id: int) -> None:
        self.conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        self.conn.commit()

    # ------------------------------------------------------------ categorías
    def categories(self, kind: str | None = None, include_archived: bool = False) -> list[dict]:
        sql = """
        SELECT c.*, (SELECT COUNT(*) FROM transactions t WHERE t.category_id = c.id) AS usage
        FROM categories c WHERE 1 = 1
        """
        params: list = []
        if kind:
            sql += " AND c.kind = ?"
            params.append(kind)
        if not include_archived:
            sql += " AND c.archived = 0"
        sql += " ORDER BY c.name COLLATE NOCASE"
        return [dict(r) for r in self.conn.execute(sql, params)]

    def get_category(self, category_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        return dict(row) if row else None

    def add_category(self, name: str, kind: str, color: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO categories (name, kind, color, archived) VALUES (?,?,?,0)",
            (name.strip(), kind, color),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_category(self, category_id: int, name: str, kind: str, color: str) -> None:
        self.conn.execute(
            "UPDATE categories SET name = ?, kind = ?, color = ? WHERE id = ?",
            (name.strip(), kind, color, category_id),
        )
        self.conn.commit()

    def set_category_archived(self, category_id: int, archived: bool) -> None:
        self.conn.execute(
            "UPDATE categories SET archived = ? WHERE id = ?", (1 if archived else 0, category_id)
        )
        self.conn.commit()

    def delete_category(self, category_id: int) -> None:
        self.conn.execute("DELETE FROM budgets WHERE category_id = ?", (category_id,))
        self.conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self.conn.commit()

    def category_usage(self, category_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE category_id = ?", (category_id,)
        ).fetchone()
        return int(row[0])

    # ------------------------------------------------------------ movimientos
    def add_transaction(self, date: str, kind: str, amount: int, category_id=None,
                        account_id=None, transfer_account_id=None,
                        description: str = "", notes: str = "",
                        transfer_amount: int | None = None,
                        recurring_id: int | None = None,
                        apply_rules: bool = True) -> int:
        if amount <= 0:
            raise ValueError("El monto debe ser mayor que cero.")
        if kind not in TYPE_LABEL:
            raise ValueError("Tipo de movimiento inválido.")

        if kind == "transferencia":
            category_id = None
            if transfer_amount is None:
                transfer_amount = self._transfer_amount(
                    int(amount), account_id, transfer_account_id, date
                )
        elif apply_rules:
            rule = self.match_rule(description, notes, kind)
            if rule:
                if rule.get("category_id"):
                    category_id = rule["category_id"]
                if rule.get("account_id"):
                    account_id = rule["account_id"]

        now = dt.datetime.now().isoformat(timespec="seconds")
        cur = self.conn.execute(
            "INSERT INTO transactions (date, kind, amount, transfer_amount, category_id,"
            " account_id, transfer_account_id, recurring_id, description, notes, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (date, kind, int(amount),
             int(transfer_amount) if transfer_amount else None,
             category_id, account_id, transfer_account_id, recurring_id,
             description.strip(), notes.strip(), now),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_transaction(self, tx_id: int, date: str, kind: str, amount: int,
                           category_id=None, account_id=None, transfer_account_id=None,
                           description: str = "", notes: str = "",
                           transfer_amount: int | None = None,
                           recurring_id=_KEEP) -> None:
        if amount <= 0:
            raise ValueError("El monto debe ser mayor que cero.")
        if kind == "transferencia":
            category_id = None
            if transfer_amount is None:
                transfer_amount = self._transfer_amount(
                    int(amount), account_id, transfer_account_id, date
                )
        if recurring_id is _KEEP:
            row = self.conn.execute(
                "SELECT recurring_id FROM transactions WHERE id = ?", (tx_id,)
            ).fetchone()
            recurring_id = row["recurring_id"] if row else None
        self.conn.execute(
            "UPDATE transactions SET date = ?, kind = ?, amount = ?, transfer_amount = ?,"
            " category_id = ?, account_id = ?, transfer_account_id = ?, recurring_id = ?,"
            " description = ?, notes = ? WHERE id = ?",
            (date, kind, int(amount),
             int(transfer_amount) if transfer_amount else None,
             category_id, account_id, transfer_account_id, recurring_id,
             description.strip(), notes.strip(), tx_id),
        )
        self.conn.commit()

    def delete_transaction(self, tx_id: int) -> None:
        self.conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        self.conn.commit()

    def get_transaction(self, tx_id: int) -> dict | None:
        row = self.conn.execute(TX_SELECT + " WHERE t.id = ?", (tx_id,)).fetchone()
        return dict(row) if row else None

    def has_transactions(self) -> bool:
        row = self.conn.execute("SELECT EXISTS(SELECT 1 FROM transactions)").fetchone()
        return bool(row[0])

    def _tx_where(self, filters: dict | None) -> tuple[str, list]:
        filters = filters or {}
        clauses: list[str] = []
        params: list = []

        query = parse_search_query(filters.get("text") or "")
        if query["text"]:
            clauses.append("(t.description LIKE ? OR t.notes LIKE ?)")
            params += [f"%{query['text']}%", f"%{query['text']}%"]
        for op, cents in query["amount_ops"]:
            if op not in {">", ">=", "<", "<=", "="}:
                continue
            clauses.append(f"t.amount {op} ?")
            params.append(int(cents))
        if query["category"]:
            clauses.append("c.name LIKE ?")
            params.append(f"%{query['category']}%")
        if query["account"]:
            clauses.append("(a.name LIKE ? OR d.name LIKE ?)")
            params += [f"%{query['account']}%", f"%{query['account']}%"]
        if query["kind"]:
            clauses.append("t.kind = ?")
            params.append(query["kind"])
        for op, iso in query["date_ops"]:
            if op not in {">", ">=", "<", "<=", "="}:
                continue
            clauses.append(f"t.date {op} ?")
            params.append(iso)

        kind = filters.get("kind")
        if kind in TYPE_LABEL:
            clauses.append("t.kind = ?")
            params.append(kind)
        category_id = filters.get("category_id")
        if category_id == 0:
            clauses.append("t.category_id IS NULL")
        elif category_id:
            clauses.append("t.category_id = ?")
            params.append(category_id)
        account_id = filters.get("account_id")
        if account_id:
            clauses.append("(t.account_id = ? OR t.transfer_account_id = ?)")
            params += [account_id, account_id]
        if filters.get("date_from"):
            clauses.append("t.date >= ?")
            params.append(filters["date_from"])
        if filters.get("date_to"):
            clauses.append("t.date <= ?")
            params.append(filters["date_to"])
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return where, params

    def transactions(self, filters: dict | None = None) -> list[dict]:
        filters = filters or {}
        where, params = self._tx_where(filters)
        sort = filters.get("sort") or "fecha"
        if sort not in SORT_COLUMNS:
            sort = "fecha"
        expr = SORT_COLUMNS[sort]
        if sort in TEXT_SORTS:
            expr += " COLLATE NOCASE"
        direction = "DESC" if filters.get("desc", True) else "ASC"
        sql = TX_SELECT + where + f" ORDER BY {expr} {direction}, t.id {direction}"
        if filters.get("limit"):
            sql += " LIMIT ?"
            params = params + [int(filters["limit"])]
            if filters.get("offset"):
                sql += " OFFSET ?"
                params = params + [int(filters["offset"])]
        return [dict(r) for r in self.conn.execute(sql, params)]

    def transaction_count(self, filters: dict | None = None) -> int:
        where, params = self._tx_where(filters)
        row = self.conn.execute(
            "SELECT COUNT(*) " + TX_FROM + where, params
        ).fetchone()
        return int(row[0])

    def transaction_totals(self, filters: dict | None = None) -> dict:
        where, params = self._tx_where(filters)
        row = self.conn.execute(
            "SELECT COUNT(*) AS n,"
            f" COALESCE(SUM(CASE WHEN t.kind = 'ingreso' THEN {_base_amount_sql()} END), 0)"
            " AS income,"
            f" COALESCE(SUM(CASE WHEN t.kind = 'egreso' THEN {_base_amount_sql()} END), 0)"
            " AS expense " + TX_FROM + where,
            params,
        ).fetchone()
        return {"count": int(row["n"]), "income": int(row["income"]), "expense": int(row["expense"])}

    # ------------------------------------------------------------ estadísticas
    def summary(self, date_from: str, date_to: str) -> dict:
        base = _base_amount_sql()
        row = self.conn.execute(
            f"SELECT COALESCE(SUM(CASE WHEN t.kind = 'ingreso' THEN {base} END), 0)"
            " AS income,"
            f" COALESCE(SUM(CASE WHEN t.kind = 'egreso' THEN {base} END), 0)"
            " AS expense"
            " FROM transactions t LEFT JOIN accounts a ON a.id = t.account_id"
            " WHERE t.date BETWEEN ? AND ?",
            (date_from, date_to),
        ).fetchone()
        income, expense = int(row["income"]), int(row["expense"])
        return {"income": income, "expense": expense, "net": income - expense}

    def monthly_series(self, months: int = 6) -> list[dict]:
        keys = recent_month_keys(months)
        start = month_bounds(keys[0])[0]
        end = month_bounds(keys[-1])[1]
        base = _base_amount_sql()
        rows = self.conn.execute(
            f"SELECT substr(t.date, 1, 7) AS ym,"
            f" COALESCE(SUM(CASE WHEN t.kind = 'ingreso' THEN {base} END), 0) AS income,"
            f" COALESCE(SUM(CASE WHEN t.kind = 'egreso' THEN {base} END), 0) AS expense"
            " FROM transactions t LEFT JOIN accounts a ON a.id = t.account_id"
            " WHERE t.date BETWEEN ? AND ? GROUP BY ym",
            (start, end),
        )
        found = {r["ym"]: r for r in rows}
        series = []
        for key in keys:
            row = found.get(key)
            series.append({
                "key": key,
                "income": int(row["income"]) if row else 0,
                "expense": int(row["expense"]) if row else 0,
            })
        return series

    def category_totals(self, kind: str, date_from: str, date_to: str) -> list[dict]:
        base = _base_amount_sql()
        rows = self.conn.execute(
            f"SELECT COALESCE(c.name, 'Sin categoría') AS name,"
            " COALESCE(c.color, '#94a3b8') AS color,"
            f" SUM({base}) AS total, COUNT(*) AS n"
            " FROM transactions t"
            " LEFT JOIN categories c ON c.id = t.category_id"
            " LEFT JOIN accounts a ON a.id = t.account_id"
            " WHERE t.kind = ? AND t.date BETWEEN ? AND ?"
            " GROUP BY COALESCE(c.id, -1), c.name, c.color"
            " ORDER BY total DESC",
            (kind, date_from, date_to),
        )
        return [
            {"name": r["name"], "color": r["color"], "total": int(r["total"]), "count": int(r["n"])}
            for r in rows
        ]

    def year_totals(self, year: int) -> list[dict]:
        base = _base_amount_sql()
        rows = self.conn.execute(
            f"SELECT substr(t.date, 6, 2) AS mm,"
            f" COALESCE(SUM(CASE WHEN t.kind = 'ingreso' THEN {base} END), 0) AS income,"
            f" COALESCE(SUM(CASE WHEN t.kind = 'egreso' THEN {base} END), 0) AS expense"
            " FROM transactions t LEFT JOIN accounts a ON a.id = t.account_id"
            " WHERE substr(t.date, 1, 4) = ? GROUP BY mm",
            (str(year),),
        )
        found = {int(r["mm"]): r for r in rows}
        result = []
        for month in range(1, 13):
            row = found.get(month)
            income = int(row["income"]) if row else 0
            expense = int(row["expense"]) if row else 0
            result.append({
                "month": month,
                "key": f"{year:04d}-{month:02d}",
                "income": income,
                "expense": expense,
                "net": income - expense,
            })
        return result

    def months_with_data(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT substr(date, 1, 7) AS m FROM transactions ORDER BY m DESC"
        )
        return [r["m"] for r in rows if r["m"]]

    def years_with_data(self) -> list[int]:
        rows = self.conn.execute(
            "SELECT DISTINCT substr(date, 1, 4) AS y FROM transactions ORDER BY y DESC"
        )
        years = [int(r["y"]) for r in rows if r["y"]]
        current = dt.date.today().year
        if current not in years:
            years.insert(0, current)
        return sorted(set(years), reverse=True)

    # ------------------------------------------------------------ presupuestos
    def budgets_for_month(self, key: str) -> list[dict]:
        date_from, date_to = month_bounds(key)
        base = _base_amount_sql("t2", "a2")
        rows = self.conn.execute(
            "SELECT c.id, c.name, c.color, COALESCE(b.amount, 0) AS budget,"
            f" COALESCE((SELECT SUM({base}) FROM transactions t2"
            "  LEFT JOIN accounts a2 ON a2.id = t2.account_id"
            "  WHERE t2.category_id = c.id AND t2.kind = 'egreso'"
            "  AND t2.date BETWEEN ? AND ?), 0) AS spent"
            " FROM categories c LEFT JOIN budgets b ON b.category_id = c.id"
            " WHERE c.kind = 'egreso' AND c.archived = 0"
            " ORDER BY CASE WHEN COALESCE(b.amount, 0) = 0 THEN 1 ELSE 0 END,"
            " c.name COLLATE NOCASE",
            (date_from, date_to),
        )
        return [dict(r) for r in rows]

    def get_budget(self, category_id: int) -> int:
        row = self.conn.execute(
            "SELECT amount FROM budgets WHERE category_id = ?", (category_id,)
        ).fetchone()
        return int(row["amount"]) if row else 0

    def set_budget(self, category_id: int, amount: int) -> None:
        if amount and amount > 0:
            self.conn.execute(
                "INSERT INTO budgets (category_id, amount) VALUES (?,?)"
                " ON CONFLICT(category_id) DO UPDATE SET amount = excluded.amount",
                (category_id, int(amount)),
            )
        else:
            self.conn.execute("DELETE FROM budgets WHERE category_id = ?", (category_id,))
        self.conn.commit()

    def budget_alerts(self, key: str, limit: int = 4) -> list[dict]:
        rows = [b for b in self.budgets_for_month(key) if b["budget"] > 0]
        rows.sort(key=lambda b: b["spent"] / b["budget"], reverse=True)
        return rows[:limit]

    # ------------------------------------------------------------ recurrentes
    def recurring(self, include_inactive: bool = True) -> list[dict]:
        sql = """
        SELECT r.*, c.name AS category_name, a.name AS account_name,
               d.name AS transfer_account_name,
               a.currency AS account_currency, d.currency AS transfer_currency
        FROM recurring r
        LEFT JOIN categories c ON c.id = r.category_id
        LEFT JOIN accounts a ON a.id = r.account_id
        LEFT JOIN accounts d ON d.id = r.transfer_account_id
        """
        if not include_inactive:
            sql += " WHERE r.active = 1"
        sql += " ORDER BY r.active DESC, r.description COLLATE NOCASE"
        return [dict(r) for r in self.conn.execute(sql)]

    def get_recurring(self, recurring_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM recurring WHERE id = ?", (recurring_id,)
        ).fetchone()
        return dict(row) if row else None

    def add_recurring(self, description: str, kind: str, amount: int, category_id,
                      account_id, transfer_account_id, frequency: str, day: int,
                      start_date: str, month: int | None = None,
                      active: bool = True) -> int:
        if amount <= 0:
            raise ValueError("El monto debe ser mayor que cero.")
        if kind not in TYPE_LABEL:
            raise ValueError("Tipo de movimiento inválido.")
        if frequency not in FREQUENCY_LABELS:
            raise ValueError("Frecuencia inválida.")
        try:
            dt.date.fromisoformat(start_date)
        except ValueError:
            raise ValueError("La fecha de inicio no es válida.")
        now = dt.datetime.now().isoformat(timespec="seconds")
        cur = self.conn.execute(
            "INSERT INTO recurring (description, kind, amount, category_id, account_id,"
            " transfer_account_id, frequency, day, month, start_date, last_run, active,"
            " created_at) VALUES (?,?,?,?,?,?,?,?,?,?,NULL,?,?)",
            (description.strip(), kind, int(amount), category_id, account_id,
             transfer_account_id, frequency, int(day), month, start_date,
             1 if active else 0, now),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_recurring(self, recurring_id: int, description: str, kind: str,
                         amount: int, category_id, account_id, transfer_account_id,
                         frequency: str, day: int, start_date: str,
                         month: int | None = None, active: bool = True) -> None:
        if amount <= 0:
            raise ValueError("El monto debe ser mayor que cero.")
        try:
            dt.date.fromisoformat(start_date)
        except ValueError:
            raise ValueError("La fecha de inicio no es válida.")
        self.conn.execute(
            "UPDATE recurring SET description = ?, kind = ?, amount = ?, category_id = ?,"
            " account_id = ?, transfer_account_id = ?, frequency = ?, day = ?, month = ?,"
            " start_date = ?, active = ? WHERE id = ?",
            (description.strip(), kind, int(amount), category_id, account_id,
             transfer_account_id, frequency, int(day), month, start_date,
             1 if active else 0, recurring_id),
        )
        self.conn.commit()

    def delete_recurring(self, recurring_id: int) -> None:
        self.conn.execute("DELETE FROM recurring WHERE id = ?", (recurring_id,))
        self.conn.commit()

    def restore_recurring(self, row: dict) -> None:
        self.conn.execute(
            "INSERT INTO recurring (id, description, kind, amount, category_id, account_id,"
            " transfer_account_id, frequency, day, month, start_date, last_run, active,"
            " created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (row["id"], row.get("description", ""), row["kind"], row["amount"],
             self._existing_ref("categories", row.get("category_id")),
             self._existing_ref("accounts", row.get("account_id")),
             self._existing_ref("accounts", row.get("transfer_account_id")),
             row.get("frequency", "mensual"), row.get("day", 1),
             row.get("month"), row.get("start_date", ""), row.get("last_run"),
             row.get("active", 1), row.get("created_at", "")),
        )
        self.conn.commit()

    def set_recurring_active(self, recurring_id: int, active: bool) -> None:
        self.conn.execute(
            "UPDATE recurring SET active = ? WHERE id = ?",
            (1 if active else 0, recurring_id),
        )
        self.conn.commit()

    def next_occurrence(self, rule: dict, after: str | None = None) -> str | None:
        after_date = dt.date.fromisoformat(after) if after else None
        return next_recurring_date(rule, after_date)

    def process_recurring(self, today: str | None = None) -> int:
        """Crea los movimientos pendientes de todas las reglas activas."""
        try:
            until = dt.date.fromisoformat(today) if today else dt.date.today()
        except ValueError:
            until = dt.date.today()
        rows = self.conn.execute(
            "SELECT * FROM recurring WHERE active = 1"
        ).fetchall()
        created = 0
        now = dt.datetime.now().isoformat(timespec="seconds")
        with self.conn:
            for raw in rows:
                rule = dict(raw)
                if not rule.get("account_id"):
                    continue
                if not rule.get("start_date"):
                    continue
                try:
                    start = dt.date.fromisoformat(rule["start_date"])
                except ValueError:
                    continue
                if rule.get("last_run"):
                    try:
                        after = dt.date.fromisoformat(rule["last_run"]) + dt.timedelta(days=1)
                    except ValueError:
                        after = start
                else:
                    after = start
                dates = list(iter_recurring_dates(rule, after, until))
                if not dates:
                    continue
                category_id = rule.get("category_id")
                if rule["kind"] == "transferencia":
                    category_id = None
                description = (rule.get("description") or "").strip()
                if not description:
                    if rule["kind"] == "transferencia":
                        description = "Transferencia recurrente"
                    else:
                        category = self.get_category(category_id) if category_id else None
                        description = category["name"] if category else "Movimiento recurrente"
                transfer_amount = None
                if rule["kind"] == "transferencia":
                    transfer_amount = self._transfer_amount(
                        int(rule["amount"]), rule["account_id"],
                        rule.get("transfer_account_id"), dates[-1].isoformat(),
                    )
                for occurrence in dates:
                    amount = int(rule["amount"])
                    dest_amount = transfer_amount
                    if rule["kind"] == "transferencia":
                        dest_amount = self._transfer_amount(
                            amount, rule["account_id"],
                            rule.get("transfer_account_id"), occurrence.isoformat(),
                        )
                    try:
                        self.conn.execute(
                            "INSERT INTO transactions (date, kind, amount, transfer_amount,"
                            " category_id, account_id, transfer_account_id, recurring_id,"
                            " description, notes, created_at)"
                            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (occurrence.isoformat(), rule["kind"], amount, dest_amount,
                             category_id, rule["account_id"],
                             rule.get("transfer_account_id"), rule["id"],
                             description, "", now),
                        )
                        created += 1
                    except sqlite3.IntegrityError:
                        # Ya existía una ocurrencia para esa fecha.
                        pass
                self.conn.execute(
                    "UPDATE recurring SET last_run = ? WHERE id = ?",
                    (dates[-1].isoformat(), rule["id"]),
                )
        return created

    # ------------------------------------------------------------ reglas
    def rules(self, include_inactive: bool = True) -> list[dict]:
        sql = """
        SELECT r.*, c.name AS category_name, a.name AS account_name
        FROM rules r
        LEFT JOIN categories c ON c.id = r.category_id
        LEFT JOIN accounts a ON a.id = r.account_id
        """
        if not include_inactive:
            sql += " WHERE r.active = 1"
        sql += " ORDER BY r.id"
        return [dict(r) for r in self.conn.execute(sql)]

    def get_rule(self, rule_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
        return dict(row) if row else None

    def add_rule(self, match_text: str, category_id=None, account_id=None,
                 active: bool = True) -> int:
        text = (match_text or "").strip()
        if not text:
            raise ValueError("Escribe el texto que debe contener el movimiento.")
        if not category_id and not account_id:
            raise ValueError("Elige una categoría o una cuenta para la regla.")
        now = dt.datetime.now().isoformat(timespec="seconds")
        cur = self.conn.execute(
            "INSERT INTO rules (match_text, category_id, account_id, active, created_at)"
            " VALUES (?,?,?,?,?)",
            (text, category_id, account_id, 1 if active else 0, now),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_rule(self, rule_id: int, match_text: str, category_id=None,
                    account_id=None, active: bool = True) -> None:
        text = (match_text or "").strip()
        if not text:
            raise ValueError("Escribe el texto que debe contener el movimiento.")
        if not category_id and not account_id:
            raise ValueError("Elige una categoría o una cuenta para la regla.")
        self.conn.execute(
            "UPDATE rules SET match_text = ?, category_id = ?, account_id = ?, active = ?"
            " WHERE id = ?",
            (text, category_id, account_id, 1 if active else 0, rule_id),
        )
        self.conn.commit()

    def delete_rule(self, rule_id: int) -> None:
        self.conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        self.conn.commit()

    def restore_rule(self, row: dict) -> None:
        self.conn.execute(
            "INSERT INTO rules (id, match_text, category_id, account_id, active, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (row["id"], row.get("match_text", ""), row.get("category_id"),
             row.get("account_id"), row.get("active", 1), row.get("created_at", "")),
        )
        self.conn.commit()

    def set_rule_active(self, rule_id: int, active: bool) -> None:
        self.conn.execute(
            "UPDATE rules SET active = ? WHERE id = ?",
            (1 if active else 0, rule_id),
        )
        self.conn.commit()

    def match_rule(self, description: str, notes: str = "",
                   kind: str | None = None) -> dict | None:
        haystack = f"{description or ''} {notes or ''}".casefold()
        if not haystack.strip():
            return None
        for rule in self.rules(include_inactive=False):
            needle = (rule.get("match_text") or "").casefold()
            if not needle or needle not in haystack:
                continue
            category_id = rule.get("category_id")
            if category_id and kind in ("ingreso", "egreso"):
                category = self.get_category(category_id)
                if not category or category["kind"] != kind:
                    # Una regla con categoría de gasto no debe aplicarse a un ingreso.
                    continue
            if not category_id and not rule.get("account_id"):
                continue
            result = dict(rule)
            result["category_id"] = category_id
            return result
        return None

    def apply_rules_to_existing(self) -> int:
        """Aplica las reglas activas a movimientos existentes (no transferencias)."""
        changed = 0
        rows = self.conn.execute(
            "SELECT id, kind, description, notes, category_id, account_id"
            " FROM transactions WHERE kind IN ('ingreso', 'egreso')"
        ).fetchall()
        with self.conn:
            for row in rows:
                rule = self.match_rule(row["description"], row["notes"], row["kind"])
                if not rule:
                    continue
                category_id = rule.get("category_id") or row["category_id"]
                account_id = rule.get("account_id") or row["account_id"]
                if category_id == row["category_id"] and account_id == row["account_id"]:
                    continue
                self.conn.execute(
                    "UPDATE transactions SET category_id = ?, account_id = ? WHERE id = ?",
                    (category_id, account_id, row["id"]),
                )
                changed += 1
        return changed

    # ------------------------------------------------------------ deshacer
    def _existing_ref(self, table: str, value):
        """Devuelve ``value`` si la fila referenciada aún existe; si no, None.

        Al deshacer un borrado puede que la cuenta o la categoría ya no existan
        (por ejemplo, se borraron después del movimiento). En ese caso se
        conserva el movimiento sin una referencia rota.
        """
        if value in (None, "", 0):
            return None
        row = self.conn.execute(
            f"SELECT 1 FROM {table} WHERE id = ?", (value,)
        ).fetchone()
        return value if row else None

    def restore_transaction(self, row: dict) -> None:
        """Reinserta un movimiento eliminado conservando su id."""
        self.conn.execute(
            "INSERT INTO transactions (id, date, kind, amount, transfer_amount, category_id,"
            " account_id, transfer_account_id, recurring_id, description, notes, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (row["id"], row["date"], row["kind"], row["amount"],
             row.get("transfer_amount"),
             self._existing_ref("categories", row.get("category_id")),
             self._existing_ref("accounts", row.get("account_id")),
             self._existing_ref("accounts", row.get("transfer_account_id")),
             self._existing_ref("recurring", row.get("recurring_id")),
             row.get("description", ""), row.get("notes", ""),
             row.get("created_at", "")),
        )
        self.conn.commit()

    def restore_category(self, row: dict, budget: int = 0) -> None:
        self.conn.execute(
            "INSERT INTO categories (id, name, kind, color, archived) VALUES (?,?,?,?,?)",
            (row["id"], row["name"], row["kind"], row.get("color", "#6366f1"),
             row.get("archived", 0)),
        )
        if budget:
            self.conn.execute(
                "INSERT OR REPLACE INTO budgets (category_id, amount) VALUES (?,?)",
                (row["id"], int(budget)),
            )
        self.conn.commit()

    def restore_account(self, row: dict) -> None:
        self.conn.execute(
            "INSERT INTO accounts (id, name, kind, initial_balance, color, currency,"
            " archived, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (row["id"], row["name"], row["kind"], row.get("initial_balance", 0),
             row.get("color", "#6366f1"), row.get("currency", ""),
             row.get("archived", 0), row.get("created_at", "")),
        )
        self.conn.commit()

    # ------------------------------------------------------------ datos de ejemplo
    def seed_demo(self, months: int = 6) -> None:
        """Genera movimientos de ejemplo realistas en los últimos meses."""
        rnd = random.Random(20261114)
        today = dt.date.today()
        self._seed_defaults()

        cats = self.categories(include_archived=True)
        by_name = {c["name"]: c["id"] for c in cats}
        by_kind: dict[str, list[int]] = {"ingreso": [], "egreso": []}
        for c in cats:
            by_kind[c["kind"]].append(c["id"])

        def cat(kind: str, name: str | None = None) -> int | None:
            if name and name in by_name:
                return by_name[name]
            return rnd.choice(by_kind[kind]) if by_kind[kind] else None

        accs = {a["name"]: a["id"] for a in self.accounts()}
        bank = accs.get("Cuenta bancaria") or next(iter(accs.values()), None)
        cash = accs.get("Efectivo") or bank
        savings = accs.get("Ahorros") or bank

        def add(day: dt.date, kind: str, amount: int, category=None, account=None,
                description: str = "", dest=None) -> None:
            self.add_transaction(
                day.isoformat(), kind, amount, category, account, dest, description, "",
                apply_rules=False,
            )

        for key in recent_month_keys(months):
            year, month = (int(x) for x in key.split("-"))
            last_day = calendar.monthrange(year, month)[1]
            max_day = min(last_day, today.day) if key == month_key() else last_day
            if max_day < 1:
                continue

            def d(day: int) -> dt.date:
                if day > max_day:
                    day = rnd.randint(1, max_day)
                return dt.date(year, month, max(1, day))

            add(d(1), "ingreso", 320000, cat("ingreso", "Salario"), bank, "Salario mensual")
            if rnd.random() < 0.65:
                add(d(rnd.randint(8, 20)), "ingreso", rnd.randint(30000, 95000),
                    cat("ingreso", "Freelance"), bank, "Proyecto freelance")
            if rnd.random() < 0.30:
                add(d(rnd.randint(10, 24)), "ingreso", rnd.randint(8000, 30000),
                    cat("ingreso", "Ventas"), cash, "Venta de artículos")

            add(d(3), "egreso", 85000, cat("egreso", "Vivienda"), bank, "Renta del departamento")
            add(d(6), "egreso", rnd.randint(3500, 6000), cat("egreso", "Servicios"),
                bank, "Internet y telefonía")
            add(d(11), "egreso", rnd.randint(4000, 8500), cat("egreso", "Servicios"),
                bank, "Luz y agua")

            for _ in range(4):
                add(d(rnd.randint(2, 27)), "egreso", rnd.randint(4500, 12000),
                    cat("egreso", "Alimentación"), rnd.choice([cash, bank]),
                    rnd.choice(["Supermercado", "Frutas y verduras", "Comida a domicilio",
                                "Panadería", "Carnicería"]))
            for _ in range(3):
                add(d(rnd.randint(2, 27)), "egreso", rnd.randint(1500, 4500),
                    cat("egreso", "Transporte"), cash, "Transporte")
            for _ in range(2):
                add(d(rnd.randint(5, 26)), "egreso", rnd.randint(2000, 7500),
                    cat("egreso", "Ocio"), bank,
                    rnd.choice(["Cine", "Salida a cenar", "Concierto", "Streaming"]))
            if rnd.random() < 0.6:
                add(d(rnd.randint(6, 24)), "egreso", rnd.randint(3000, 14000),
                    cat("egreso", "Compras"), bank, "Compra en línea")
            if rnd.random() < 0.35:
                add(d(rnd.randint(4, 25)), "egreso", rnd.randint(4000, 11000),
                    cat("egreso", "Salud"), bank, "Consulta médica")

            add(d(5), "transferencia", 30000, None, bank, "Ahorro mensual", savings)
            if cash != bank:
                add(d(2), "transferencia", 60000, None, bank, "Retiro de efectivo", cash)

        # presupuestos de ejemplo, solo si aún no existen
        if not self.conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0]:
            for name, amount in {
                "Vivienda": 90000, "Alimentación": 30000, "Transporte": 12000,
                "Servicios": 20000, "Ocio": 15000, "Compras": 12000,
            }.items():
                category_id = by_name.get(name)
                if category_id:
                    self.set_budget(category_id, amount)

    # ------------------------------------------------------------ respaldos
    def backup_json(self, path: str | Path) -> None:
        tables = {}
        for table in ("settings", "accounts", "categories", "transactions", "budgets",
                      "fx_rates", "recurring", "rules"):
            tables[table] = [dict(r) for r in self.conn.execute(f"SELECT * FROM {table}")]
        payload = {
            "app": "finanzas",
            "version": 2,
            "exported_at": dt.datetime.now().isoformat(timespec="seconds"),
            "data": tables,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    def restore_json(self, path: str | Path) -> None:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, dict) or payload.get("app") != "finanzas":
            raise ValueError("El archivo no es un respaldo válido de Finanzas.")
        data = payload.get("data") or {}
        required = ("accounts", "categories", "transactions")
        if any(not isinstance(data.get(t), list) for t in required):
            raise ValueError("El respaldo está incompleto o dañado.")

        with self.conn:
            self.conn.execute("DELETE FROM transactions")
            self.conn.execute("DELETE FROM budgets")
            self.conn.execute("DELETE FROM recurring")
            self.conn.execute("DELETE FROM rules")
            self.conn.execute("DELETE FROM fx_rates")
            self.conn.execute("DELETE FROM categories")
            self.conn.execute("DELETE FROM accounts")
            self.conn.execute("DELETE FROM settings")
            for row in data.get("settings", []):
                self.conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?,?)",
                    (row["key"], row["value"]),
                )
            for row in data["accounts"]:
                self.conn.execute(
                    "INSERT INTO accounts (id, name, kind, initial_balance, color, currency,"
                    " archived, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (row["id"], row["name"], row["kind"], row.get("initial_balance", 0),
                     row.get("color", "#6366f1"), row.get("currency", ""),
                     row.get("archived", 0), row.get("created_at", "")),
                )
            for row in data["categories"]:
                self.conn.execute(
                    "INSERT INTO categories (id, name, kind, color, archived)"
                    " VALUES (?,?,?,?,?)",
                    (row["id"], row["name"], row["kind"], row.get("color", "#6366f1"),
                     row.get("archived", 0)),
                )
            for row in data.get("recurring", []):
                self.conn.execute(
                    "INSERT INTO recurring (id, description, kind, amount, category_id,"
                    " account_id, transfer_account_id, frequency, day, month, start_date,"
                    " last_run, active, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (row["id"], row.get("description", ""), row["kind"], row["amount"],
                     row.get("category_id"), row.get("account_id"),
                     row.get("transfer_account_id"), row.get("frequency", "mensual"),
                     row.get("day", 1), row.get("month"), row.get("start_date", ""),
                     row.get("last_run"), row.get("active", 1), row.get("created_at", "")),
                )
            for row in data.get("rules", []):
                self.conn.execute(
                    "INSERT INTO rules (id, match_text, category_id, account_id, active,"
                    " created_at) VALUES (?,?,?,?,?,?)",
                    (row["id"], row.get("match_text", ""), row.get("category_id"),
                     row.get("account_id"), row.get("active", 1), row.get("created_at", "")),
                )
            for row in data.get("fx_rates", []):
                self.conn.execute(
                    "INSERT INTO fx_rates (currency, date, rate_micros) VALUES (?,?,?)",
                    (row["currency"], row["date"], row["rate_micros"]),
                )
            for row in data["transactions"]:
                self.conn.execute(
                    "INSERT INTO transactions (id, date, kind, amount, transfer_amount,"
                    " category_id, account_id, transfer_account_id, recurring_id,"
                    " description, notes, created_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (row["id"], row["date"], row["kind"], row["amount"],
                     row.get("transfer_amount"), row.get("category_id"),
                     row.get("account_id"), row.get("transfer_account_id"),
                     row.get("recurring_id"), row.get("description", ""),
                     row.get("notes", ""), row.get("created_at", "")),
                )
            for row in data.get("budgets", []):
                self.conn.execute(
                    "INSERT INTO budgets (category_id, amount) VALUES (?,?)",
                    (row["category_id"], row.get("amount", 0)),
                )
        self._seed_defaults()

    def wipe_data(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM transactions")
            self.conn.execute("DELETE FROM budgets")
            self.conn.execute("DELETE FROM recurring")
            self.conn.execute("DELETE FROM rules")
            self.conn.execute("DELETE FROM fx_rates")
            self.conn.execute("DELETE FROM categories")
            self.conn.execute("DELETE FROM accounts")
        self._seed_defaults()

    def export_csv(self, path: str | Path, filters: dict | None = None) -> int:
        rows = self.transactions(filters or {})
        style = self.get_setting("number_format", "en") or "en"
        base_code = self.base_currency()

        def fmt(cents) -> str:
            return localize_number(f"{int(cents or 0) / 100:.2f}", style)

        def code(value) -> str:
            return (value or "").strip().upper() or base_code

        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                "Fecha", "Tipo", "Descripción", "Categoría", "Cuenta", "Moneda",
                "Monto", "Cuenta destino", "Moneda destino", "Monto destino",
                "Monto base", "Notas",
            ])
            for r in rows:
                dest_amount = r.get("transfer_amount") or (
                    r["amount"] if r["kind"] == "transferencia" else None
                )
                writer.writerow([
                    r["date"],
                    TYPE_LABEL.get(r["kind"], r["kind"]),
                    r["description"],
                    r["category_name"] or "",
                    r["account_name"] or "",
                    code(r.get("account_currency")),
                    fmt(r["amount"]),
                    r["transfer_account_name"] or "",
                    code(r.get("transfer_currency")) if r.get("transfer_currency") is not None else "",
                    fmt(dest_amount) if dest_amount is not None else "",
                    fmt(self.to_base(r["amount"], r.get("account_currency"), r["date"])),
                    r["notes"] or "",
                ])
        return len(rows)
