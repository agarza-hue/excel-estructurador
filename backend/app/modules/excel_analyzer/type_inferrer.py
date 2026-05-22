import re
from datetime import datetime
from typing import Any


DATE_PATTERNS = [
    r"^\d{4}-\d{2}-\d{2}$",
    r"^\d{2}/\d{2}/\d{4}$",
    r"^\d{2}-\d{2}-\d{4}$",
    r"^\d{1,2}/\d{1,2}/\d{2,4}$",
]

CURRENCY_PATTERN = re.compile(r"^[$€£¥₱₩₨\s]*[\d,]+\.?\d*$")
PERCENT_PATTERN = re.compile(r"^\d+\.?\d*\s*%$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_PATTERN = re.compile(r"^[\+\d\s\(\)\-\.]{7,20}$")
ID_PATTERN = re.compile(r"^[A-Z0-9\-_]{3,20}$")


def infer_cell_type(value: Any) -> str:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return "null"

    if isinstance(value, bool):
        return "boolean"

    if isinstance(value, int):
        return "integer"

    if isinstance(value, float):
        return "decimal"

    if isinstance(value, datetime):
        return "datetime"

    s = str(value).strip()

    # Try numeric
    try:
        int(s.replace(",", ""))
        return "integer"
    except ValueError:
        pass

    try:
        float(s.replace(",", ""))
        return "decimal"
    except ValueError:
        pass

    # Date
    for pattern in DATE_PATTERNS:
        if re.match(pattern, s):
            return "date"

    # Special
    if PERCENT_PATTERN.match(s):
        return "percent"
    if CURRENCY_PATTERN.match(s):
        return "currency"
    if EMAIL_PATTERN.match(s):
        return "email"
    if PHONE_PATTERN.match(s):
        return "phone"

    # Long text vs short
    if len(s) > 100:
        return "text_long"
    if len(s) <= 3 and s.isalpha():
        return "code"

    return "text"


def infer_column_type(values: list) -> dict:
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_null:
        return {"type": "unknown", "null_rate": 1.0}

    type_counts: dict[str, int] = {}
    for v in non_null:
        t = infer_cell_type(v)
        type_counts[t] = type_counts.get(t, 0) + 1

    dominant = max(type_counts, key=lambda k: type_counts[k])
    dominant_pct = type_counts[dominant] / len(non_null)

    null_rate = round(1 - len(non_null) / len(values), 3)

    # Check uniqueness
    unique_vals = set(str(v) for v in non_null)
    cardinality = len(unique_vals)
    is_unique = cardinality == len(non_null)
    is_low_cardinality = cardinality <= 20 and len(non_null) > 20

    return {
        "type": dominant,
        "confidence": round(dominant_pct, 2),
        "null_rate": null_rate,
        "cardinality": cardinality,
        "total_values": len(values),
        "non_null": len(non_null),
        "is_unique": is_unique,
        "is_low_cardinality": is_low_cardinality,
        "type_distribution": {k: round(v / len(non_null), 2) for k, v in type_counts.items()},
    }


def suggest_sql_type(col_meta: dict) -> str:
    t = col_meta.get("type", "text")
    mapping = {
        "integer": "BIGINT",
        "decimal": "NUMERIC(18,4)",
        "currency": "NUMERIC(18,2)",
        "percent": "NUMERIC(7,4)",
        "date": "DATE",
        "datetime": "TIMESTAMPTZ",
        "boolean": "BOOLEAN",
        "email": "VARCHAR(256)",
        "phone": "VARCHAR(32)",
        "code": "VARCHAR(16)",
        "text": "VARCHAR(512)",
        "text_long": "TEXT",
        "null": "TEXT",
        "unknown": "TEXT",
    }
    return mapping.get(t, "TEXT")
