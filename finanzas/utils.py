"""Utilidades de fechas, montos, búsqueda y formato."""
from __future__ import annotations

import calendar
import datetime as dt
import re
import shlex
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
MESES_CORTOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

FREQUENCY_LABELS = {
    "mensual": "Mensual",
    "quincenal": "Quincenal",
    "semanal": "Semanal",
    "anual": "Anual",
}

CURRENCY_SYMBOLS = {
    "USD": "US$", "EUR": "€", "GBP": "£", "MXN": "MX$", "ARS": "AR$",
    "CLP": "CL$", "COP": "CO$", "PEN": "S/", "BRL": "R$", "UYU": "$U",
    "PYG": "₲", "BOB": "Bs", "CRC": "₡", "DOP": "RD$", "GTQ": "Q",
    "HNL": "L", "NIO": "C$", "PAB": "B/.", "VES": "Bs.", "JPY": "¥",
    "CNY": "CN¥", "CAD": "CA$", "AUD": "A$", "CHF": "CHF ", "INR": "₹",
}


# ---------------------------------------------------------------- fechas
def today_iso() -> str:
    return dt.date.today().isoformat()


def parse_date(text: str) -> dt.date:
    """Acepta dd/mm/aaaa, dd-mm-aa, aaaa-mm-dd y palabras como hoy/ayer."""
    raw = (text or "").strip()
    low = raw.lower()
    if low in {"hoy", "today"}:
        return dt.date.today()
    if low in {"ayer", "yesterday"}:
        return dt.date.today() - dt.timedelta(days=1)

    cleaned = raw.replace(".", "/").replace("-", "/").replace(" ", "")
    parts = [p for p in cleaned.split("/") if p]
    if len(parts) == 3:
        a, b, c = parts
        try:
            if len(a) == 4:
                return dt.date(int(a), int(b), int(c))
            year = int(c)
            if len(c) == 2:
                year += 2000
            return dt.date(year, int(b), int(a))
        except ValueError:
            pass
    raise ValueError("Fecha inválida. Usa el formato dd/mm/aaaa.")


def fmt_date(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso or ""


def fmt_date_short(iso: str) -> str:
    try:
        d = dt.date.fromisoformat(iso)
    except (ValueError, TypeError):
        return iso or ""
    today = dt.date.today()
    if d == today:
        return "Hoy"
    if d == today - dt.timedelta(days=1):
        return "Ayer"
    return d.strftime("%d/%m")


# ---------------------------------------------------------------- montos
def parse_amount(text: str, allow_zero: bool = False) -> int:
    """Convierte texto a centavos (int). Lanza ValueError si es inválido."""
    s = (text or "").strip()
    if s.startswith("-"):
        raise ValueError("El monto debe ser mayor que cero.")
    s = re.sub(r"[\s$€£¥₲₡₹]", "", s).replace("'", "")
    if not s or not re.fullmatch(r"[\d.,]+", s):
        raise ValueError("Escribe un monto válido, por ejemplo 1250.50")

    has_dot, has_comma = "." in s, "," in s
    if has_dot and has_comma:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_comma:
        if s.count(",") == 1 and len(s.split(",")[-1]) <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_dot:
        pieces = s.split(".")
        if len(pieces) > 2 or (len(pieces) == 2 and len(pieces[1]) > 2):
            s = s.replace(".", "")

    try:
        value = Decimal(s)
    except InvalidOperation:
        raise ValueError("Escribe un monto válido, por ejemplo 1250.50")
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError("El monto debe ser mayor que cero.")
    return int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def localize_number(text: str, style: str = "en") -> str:
    """Convierte separadores 1,234.56 <-> 1.234,56."""
    if style != "es":
        return text
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def money(cents: int, symbol: str = "$", decimals: int = 2, plus: bool = False,
          style: str = "en") -> str:
    cents = int(cents or 0)
    value = cents / 100
    body = localize_number(f"{abs(value):,.{decimals}f}", style)
    if value < 0:
        return f"-{symbol}{body}"
    if plus and value > 0:
        return f"+{symbol}{body}"
    return f"{symbol}{body}"


def money_input(cents: int, style: str = "en") -> str:
    if not cents:
        return ""
    return localize_number(f"{int(cents) / 100:.2f}", style)


def money_compact(cents: int, symbol: str = "", style: str = "en") -> str:
    value = int(cents or 0) / 100
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}{symbol}{localize_number(f'{value / 1_000_000:.1f}', style)}M"
    if value >= 1000:
        return f"{sign}{symbol}{localize_number(f'{value / 1000:.1f}', style)}k"
    return f"{sign}{symbol}{localize_number(f'{value:,.0f}', style)}"


def currency_symbol(code: str, base_symbol: str = "$") -> str:
    """Símbolo legible para un código ISO; vacío significa moneda base."""
    code = (code or "").strip().upper()
    if not code:
        return base_symbol
    return CURRENCY_SYMBOLS.get(code, f"{code} ")


def pct(part: int, whole: int) -> float:
    if not whole:
        return 0.0
    return (part / whole) * 100


def pct_text(part: int, whole: int) -> str:
    return f"{pct(part, whole):.0f}%"


# ---------------------------------------------------------------- búsqueda avanzada
_SEARCH_RE = re.compile(
    r"^(monto|categor(?:ia|ía)|cuenta|tipo|fecha|texto)\s*(>=|<=|>|<|=|:)\s*(.+)$",
    re.IGNORECASE,
)
_KIND_ALIASES = {
    "ingreso": "ingreso", "ingresos": "ingreso",
    "egreso": "egreso", "egresos": "egreso",
    "gasto": "egreso", "gastos": "egreso",
    "transferencia": "transferencia", "transferencias": "transferencia",
}


def parse_search_query(text: str) -> dict:
    """Separa texto libre de operadores: monto>100, categoria:Ocio, etc.

    Devuelve un diccionario con listas de condiciones. Es deliberadamente
    tolerante: un operador mal escrito se trata como texto libre para no
    interrumpir la escritura.
    """
    raw = (text or "").strip()
    result = {
        "text": "",
        "amount_ops": [],
        "category": None,
        "account": None,
        "kind": None,
        "date_ops": [],
    }
    if not raw:
        return result

    try:
        tokens = shlex.split(raw)
    except ValueError:
        tokens = raw.split()

    free: list[str] = []
    for token in tokens:
        match = _SEARCH_RE.match(token.strip())
        if not match:
            free.append(token)
            continue
        field, op, value = match.group(1).lower(), match.group(2), match.group(3).strip()
        if field in {"categoria", "categoría"}:
            if value:
                result["category"] = value
            else:
                free.append(token)
        elif field == "cuenta":
            if value:
                result["account"] = value
            else:
                free.append(token)
        elif field == "tipo":
            kind = _KIND_ALIASES.get(value.casefold())
            if kind:
                result["kind"] = kind
            else:
                free.append(token)
        elif field == "texto":
            if value:
                free.append(value)
        elif field == "monto":
            try:
                cents = parse_amount(value, allow_zero=True)
            except ValueError:
                free.append(token)
            else:
                result["amount_ops"].append(("=" if op == ":" else op, cents))
        elif field == "fecha":
            ops = op if op != ":" else "="
            try:
                if ops == "=" and re.fullmatch(r"\d{4}", value):
                    result["date_ops"].extend([
                        (">=", f"{value}-01-01"), ("<=", f"{value}-12-31"),
                    ])
                elif ops == "=" and re.fullmatch(r"\d{4}-\d{2}", value):
                    year, month = (int(x) for x in value.split("-"))
                    last = calendar.monthrange(year, month)[1]
                    result["date_ops"].extend([
                        (">=", f"{value}-01"), ("<=", f"{value}-{last:02d}"),
                    ])
                else:
                    result["date_ops"].append((ops, parse_date(value).isoformat()))
            except ValueError:
                free.append(token)

    result["text"] = " ".join(free).strip()
    return result


# ---------------------------------------------------------------- moneda local
def _clamp_day(year: int, month: int, day: int) -> int:
    return max(1, min(int(day or 1), calendar.monthrange(year, month)[1]))


def _date_in_month(year: int, month: int, day: int) -> dt.date:
    return dt.date(year, month, _clamp_day(year, month, day))


def iter_recurring_dates(rule: dict, after: dt.date, until: dt.date,
                         limit: int = 600):
    """Fechas de una regla recurrente entre ``after`` y ``until`` (incluidos).

    ``after`` debe ser el día siguiente al último generado (o la fecha de
    inicio). Se respeta ``start_date`` y se limita la cantidad de resultados.
    """
    try:
        start = dt.date.fromisoformat(rule["start_date"])
    except (KeyError, ValueError, TypeError):
        return
    lower = max(start, after)
    if lower > until:
        return

    frequency = rule.get("frequency", "mensual")
    day = int(rule.get("day") or 1)
    month = int(rule.get("month") or 1)
    produced = 0

    if frequency in {"mensual", "quincenal"}:
        year, month_cursor = lower.year, lower.month
        while True:
            candidates = ([1, 16] if frequency == "quincenal"
                          else [_clamp_day(year, month_cursor, day)])
            for candidate_day in candidates:
                candidate = _date_in_month(year, month_cursor, candidate_day)
                if lower <= candidate <= until:
                    yield candidate
                    produced += 1
                    if produced >= limit:
                        return
                elif candidate > until:
                    return
            month_cursor += 1
            if month_cursor == 13:
                year, month_cursor = year + 1, 1
            if _date_in_month(year, month_cursor, 1) > until:
                return

    elif frequency == "semanal":
        target = int(rule.get("day") or 0) % 7
        candidate = lower + dt.timedelta(days=(target - lower.weekday()) % 7)
        while candidate <= until:
            yield candidate
            produced += 1
            if produced >= limit:
                return
            candidate += dt.timedelta(days=7)

    elif frequency == "anual":
        year = lower.year
        while True:
            candidate = _date_in_month(year, month, day)
            if candidate >= lower and candidate <= until:
                yield candidate
                produced += 1
                if produced >= limit:
                    return
            if candidate > until:
                return
            year += 1


def next_recurring_date(rule: dict, after: dt.date | None = None) -> str | None:
    """Primera fecha futura (o de hoy) de la regla, en ISO."""
    after = after or dt.date.today()
    try:
        start = dt.date.fromisoformat(rule["start_date"])
    except (KeyError, ValueError, TypeError):
        return None
    lower = max(after, start)
    horizon = lower + dt.timedelta(days=366 * 3 + 2)
    for candidate in iter_recurring_dates(rule, lower, horizon):
        return candidate.isoformat()
    return None


def recurring_schedule_text(rule: dict) -> str:
    frequency = rule.get("frequency", "mensual")
    day = int(rule.get("day") or 1)
    if frequency == "quincenal":
        return "Quincenal · días 1 y 16"
    if frequency == "semanal":
        return f"Semanal · {DIAS_SEMANA[day % 7].lower()}"
    if frequency == "anual":
        return f"Anual · {int(rule.get('month') or 1):02d}/{day:02d}"
    return f"Mensual · día {day}"


# ---------------------------------------------------------------- meses
def month_key(value=None) -> str:
    if value is None:
        d = dt.date.today()
    elif isinstance(value, dt.date):
        d = value
    else:
        d = dt.date.fromisoformat(str(value))
    return d.strftime("%Y-%m")


def month_bounds(key: str) -> tuple[str, str]:
    year, month = (int(x) for x in key.split("-"))
    if month == 12:
        nxt = dt.date(year + 1, 1, 1)
    else:
        nxt = dt.date(year, month + 1, 1)
    last = nxt - dt.timedelta(days=1)
    return dt.date(year, month, 1).isoformat(), last.isoformat()


def shift_month(key: str, delta: int) -> str:
    year, month = (int(x) for x in key.split("-"))
    index = year * 12 + (month - 1) + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def month_name(key: str, short: bool = False) -> str:
    year, month = (int(x) for x in key.split("-"))
    name = MESES_CORTOS[month - 1] if short else MESES[month - 1]
    return f"{name} {year}"


def recent_month_keys(count: int = 6, end: str | None = None) -> list[str]:
    key = end or month_key()
    return [shift_month(key, -i) for i in range(count - 1, -1, -1)]


def truncate(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[: max(0, limit - 1)].rstrip() + "…"
