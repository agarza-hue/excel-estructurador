"""Map the analyzer's rich sheet metadata onto the four structural categories
the upload wizard speaks to the user.

These are *layout* shapes (how the data sits on the grid), distinct from the
analyzer's *purpose* classification (master / transactional / dashboard).

  clean         a single header row over one rectangular block — import as-is
  multi_header  merged / stacked header rows that need flattening
  cross_tab     a pivoted / matrix layout (periods as columns) to unpivot
  multi_section several stacked tables on one sheet — needs splitting
"""
import re
from typing import Any

STRUCTURE_LABELS = {
    "clean": "tabla limpia",
    "multi_header": "multi-header",
    "cross_tab": "cross-tab",
    "multi_section": "multi-sección",
    "empty": "vacía",
}

_MONTHS = (
    "ene feb mar abr may jun jul ago sep oct nov dic "
    "jan apr aug dec "
    "enero febrero marzo abril mayo junio julio agosto "
    "septiembre octubre noviembre diciembre "
    "january february march april june july august september "
    "october november december"
).split()
_PERIOD_RE = re.compile(r"^(q[1-4]|t[1-4]|fy|20\d{2}|19\d{2}|\d{4})", re.IGNORECASE)


def _range_rows(ref: str) -> tuple[int, int]:
    """Top and bottom 1-based row of an A1 range like 'B2:D2' or 'A1'."""
    rows = [int(m) for m in re.findall(r"\d+", ref)]
    if not rows:
        return (0, 0)
    return (min(rows), max(rows))


def _header_area_merges(sheet: dict) -> int:
    """Count merged ranges that touch the header band (header row ± 1)."""
    header_row = sheet.get("header_row", 0) + 1  # to 1-based
    band_top, band_bottom = max(1, header_row - 1), header_row + 1
    count = 0
    for ref in sheet.get("merged_ranges", []):
        top, bottom = _range_rows(ref)
        if top <= band_bottom and bottom >= band_top:
            count += 1
    return count


def _looks_like_period_label(name: str) -> bool:
    n = (name or "").strip().lower()
    if _PERIOD_RE.match(n):
        return True
    return any(n.startswith(m) or n == m for m in _MONTHS)


def _cross_tab_score(sheet: dict) -> bool:
    """Heuristic: first column is a label, and most remaining headers look like
    periods/categories rather than attributes — i.e. a pivoted matrix."""
    cols = sheet.get("columns_meta", [])
    if len(cols) < 3:
        return False
    first_is_label = cols[0].get("type") in ("text", "code", "categorical", "string")
    rest = cols[1:]
    period_headers = sum(1 for c in rest if _looks_like_period_label(c.get("name", "")))
    numeric_rest = sum(
        1 for c in rest
        if c.get("type") in ("integer", "decimal", "currency", "percent", "number")
    )
    if not first_is_label:
        return False
    # Either the headers are literally periods, or nearly every non-first column
    # is numeric (classic value-matrix).
    return period_headers >= 2 or numeric_rest >= max(2, int(0.8 * len(rest)))


def classify_structure(sheet: dict) -> tuple[str, list[str]]:
    """Return (structure_type, human-readable reasons)."""
    if sheet.get("sheet_type") == "empty" or sheet.get("row_count", 0) == 0:
        return "empty", ["la hoja no contiene datos"]

    reasons: list[str] = []

    # 1. Several stacked data blocks → multi-section.
    regions = [r for r in sheet.get("regions", []) if r.get("row_count", 0) >= 2]
    if len(regions) >= 2:
        reasons.append(f"{len(regions)} bloques de datos separados detectados")
        return "multi_section", reasons

    # 2. Pivot table object present → cross-tab.
    if sheet.get("has_pivot_table"):
        reasons.append("la hoja contiene una tabla dinámica (pivot)")
        return "cross_tab", reasons

    # 3. Merged cells in the header band → stacked / multi-header.
    header_merges = _header_area_merges(sheet)
    if header_merges >= 1:
        reasons.append(f"{header_merges} celda(s) combinada(s) en la fila de encabezados")
        return "multi_header", reasons

    # 4. Header not on the first row → likely title rows / banner above the table.
    if sheet.get("header_row", 0) >= 2:
        reasons.append(f"encabezados detectados en la fila {sheet['header_row'] + 1}")
        return "multi_header", reasons

    # 5. Pivoted value-matrix → cross-tab.
    if _cross_tab_score(sheet):
        reasons.append("primera columna es etiqueta y el resto son valores por período")
        return "cross_tab", reasons

    reasons.append("una sola fila de encabezados sobre un bloque rectangular")
    return "clean", reasons
