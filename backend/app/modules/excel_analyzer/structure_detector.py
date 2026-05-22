from typing import Any
import re


def detect_header_row(rows: list[list[Any]], max_scan: int = 10) -> int:
    """Find the most likely header row index."""
    best_row = 0
    best_score = -1

    for i, row in enumerate(rows[:max_scan]):
        if not row:
            continue
        non_empty = [c for c in row if c is not None and str(c).strip() != ""]
        if not non_empty:
            continue

        score = 0
        # All text cells = likely header
        text_count = sum(1 for c in non_empty if isinstance(c, str))
        score += text_count * 2

        # No numeric-only cells
        num_count = sum(1 for c in non_empty if isinstance(c, (int, float)) and not isinstance(c, bool))
        score -= num_count * 3

        # Short strings typical of headers
        short_text = sum(1 for c in non_empty if isinstance(c, str) and len(c) <= 50)
        score += short_text

        # Capitalized
        cap_count = sum(1 for c in non_empty if isinstance(c, str) and c[0:1].isupper())
        score += cap_count

        if score > best_score:
            best_score = score
            best_row = i

    return best_row


def detect_table_regions(rows: list[list[Any]]) -> list[dict]:
    """Find contiguous rectangular data regions."""
    regions = []
    in_region = False
    region_start = 0
    empty_streak = 0

    for i, row in enumerate(rows):
        is_empty = all(c is None or str(c).strip() == "" for c in row)

        if not is_empty:
            if not in_region:
                region_start = i
                in_region = True
            empty_streak = 0
        else:
            empty_streak += 1
            if in_region and empty_streak >= 3:
                regions.append({
                    "start_row": region_start,
                    "end_row": i - empty_streak,
                    "row_count": (i - empty_streak) - region_start + 1,
                })
                in_region = False
                empty_streak = 0

    if in_region:
        regions.append({
            "start_row": region_start,
            "end_row": len(rows) - 1,
            "row_count": len(rows) - region_start,
        })

    return regions


def classify_sheet_type(sheet_meta: dict) -> tuple[str, float]:
    """Heuristic classification of sheet purpose."""
    name_lower = sheet_meta.get("sheet_name", "").lower()
    col_count = sheet_meta.get("col_count", 0)
    row_count = sheet_meta.get("row_count", 0)
    has_formulas = sheet_meta.get("has_formulas", False)
    formula_count = sheet_meta.get("formula_count", 0)
    has_pivot = sheet_meta.get("has_pivot_table", False)
    columns_meta = sheet_meta.get("columns_meta", [])

    # Name-based clues
    master_keywords = ["catalog", "catálogo", "master", "maestro", "list", "lista",
                       "config", "configuración", "param", "parámetro", "lookup"]
    transactional_keywords = ["transaction", "transacción", "order", "pedido", "invoice",
                               "factura", "sale", "venta", "purchase", "compra", "detail",
                               "detalle", "log", "registro", "history", "historial"]
    dashboard_keywords = ["dashboard", "resumen", "summary", "report", "reporte",
                          "kpi", "indicador", "análisis", "analysis", "overview"]

    for kw in master_keywords:
        if kw in name_lower:
            return "master", 0.85

    for kw in dashboard_keywords:
        if kw in name_lower:
            return "dashboard", 0.85

    for kw in transactional_keywords:
        if kw in name_lower:
            return "transactional", 0.85

    # Structure-based classification
    if has_pivot:
        return "dashboard", 0.75

    # Many formulas + few columns = likely aggregation/report
    formula_density = formula_count / max(row_count * col_count, 1)
    if formula_density > 0.3:
        return "dashboard", 0.65

    # Many rows, fixed columns = transactional
    if row_count > 50 and 3 <= col_count <= 30:
        # Check if first column looks like an ID
        if columns_meta:
            first_col = columns_meta[0] if columns_meta else {}
            if first_col.get("is_unique") and first_col.get("type") in ("integer", "code", "text"):
                return "transactional", 0.70

    # Small, mostly text = master/catalog
    if row_count <= 50 and col_count <= 10:
        return "master", 0.60

    if row_count > 100:
        return "transactional", 0.55

    return "unknown", 0.40


def detect_relationships(sheets_meta: list[dict]) -> list[dict]:
    """Detect potential FK-like relationships between sheets based on column names."""
    relationships = []

    # Build column name index
    sheet_cols: dict[str, set[str]] = {}
    for s in sheets_meta:
        name = s.get("sheet_name", "")
        cols = {c.get("name", "").lower() for c in s.get("columns_meta", [])}
        sheet_cols[name] = cols

    sheets = list(sheet_cols.keys())
    for i, sheet_a in enumerate(sheets):
        for sheet_b in sheets[i + 1:]:
            common = sheet_cols[sheet_a] & sheet_cols[sheet_b]
            # Filter out generic names
            meaningful = {c for c in common if len(c) > 2 and c not in
                         ("id", "name", "date", "total", "amount", "qty", "quantity",
                          "nombre", "fecha", "total", "monto")}
            if meaningful:
                relationships.append({
                    "sheet_a": sheet_a,
                    "sheet_b": sheet_b,
                    "shared_columns": list(meaningful),
                    "relationship_type": "potential_join",
                })

    return relationships


def sanitize_column_name(name: str) -> str:
    """Convert Excel header to a valid SQL column name."""
    if not name:
        return "col_unknown"
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if name and name[0].isdigit():
        name = "col_" + name
    return name or "col_unknown"
