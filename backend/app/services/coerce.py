"""Coerce raw cell/form values to the type declared by a schema field.

Returns (coerced_value, warning). A warning is a human string when the value
looked wrong for the declared type — surfaced in the wizard's inline validation
and in ingestion reports, never silently dropped.
"""
import re
from datetime import date, datetime
from typing import Any

from app.services.schema_store import SchemaField

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d")
_NUM_CLEAN = re.compile(r"[^\d,.\-]")


def _to_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    s = _NUM_CLEAN.sub("", str(value)).strip()
    if not s:
        return None
    # 1.234,56 (es) vs 1,234.56 (en)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def _to_date(value: Any) -> str | None:
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def coerce_value(field: SchemaField, value: Any) -> tuple[Any, str | None]:
    is_empty = value is None or (isinstance(value, str) and value.strip() == "")
    if is_empty:
        if field.required:
            return None, f"'{field.label}' es requerido y está vacío"
        return None, None

    try:
        if field.type in ("number", "currency"):
            n = _to_number(value)
            if n is None:
                return value, f"'{field.label}': '{value}' no es un número válido"
            return n, None

        if field.type == "date":
            d = _to_date(value)
            if d is None:
                return value, f"'{field.label}': '{value}' no es una fecha reconocible"
            return d, None

        if field.type == "boolean":
            s = str(value).strip().lower()
            if s in ("true", "1", "si", "sí", "yes", "y", "x", "verdadero"):
                return True, None
            if s in ("false", "0", "no", "n", "falso"):
                return False, None
            return value, f"'{field.label}': '{value}' no es booleano"

        if field.type == "select":
            if field.options and str(value) not in field.options:
                return value, f"'{field.label}': '{value}' no está entre las opciones permitidas"
            return str(value), None

        return str(value), None
    except Exception as exc:  # defensive — never crash a whole import on one cell
        return value, f"'{field.label}': error al convertir '{value}' ({exc})"
