import re
from typing import Any


EXCEL_FUNCTIONS = {
    # Financial
    "financial": ["NPV", "IRR", "PMT", "PV", "FV", "RATE", "NPER", "XIRR", "XNPV", "MIRR"],
    # Statistical
    "statistical": ["SUM", "AVERAGE", "COUNT", "COUNTA", "COUNTIF", "COUNTIFS", "SUMIF", "SUMIFS",
                    "AVERAGEIF", "AVERAGEIFS", "MAX", "MIN", "MEDIAN", "STDEV", "STDEVP", "VAR", "VARP"],
    # Lookup
    "lookup": ["VLOOKUP", "HLOOKUP", "INDEX", "MATCH", "XLOOKUP", "OFFSET", "INDIRECT", "CHOOSE"],
    # Date
    "date": ["TODAY", "NOW", "DATE", "YEAR", "MONTH", "DAY", "EDATE", "EOMONTH", "DATEDIF",
             "NETWORKDAYS", "WORKDAY", "WEEKDAY", "TEXT"],
    # Logic
    "logic": ["IF", "IFS", "IFERROR", "IFNA", "AND", "OR", "NOT", "TRUE", "FALSE", "SWITCH"],
    # Text
    "text": ["CONCATENATE", "CONCAT", "TEXTJOIN", "LEFT", "RIGHT", "MID", "LEN", "TRIM", "UPPER",
             "LOWER", "PROPER", "FIND", "SEARCH", "REPLACE", "SUBSTITUTE"],
    # Math
    "math": ["ROUND", "ROUNDUP", "ROUNDDOWN", "ABS", "MOD", "INT", "CEILING", "FLOOR", "POWER",
             "SQRT", "EXP", "LN", "LOG", "RAND", "RANDBETWEEN"],
    # Database
    "database": ["DSUM", "DAVERAGE", "DCOUNT", "DGET", "DMAX", "DMIN"],
    # Array
    "array": ["FILTER", "SORT", "UNIQUE", "SEQUENCE", "TRANSPOSE", "MMULT", "SUMPRODUCT"],
}

FUNCTION_FLAT = {f: cat for cat, funcs in EXCEL_FUNCTIONS.items() for f in funcs}
CROSS_SHEET_RE = re.compile(r"'?([^'!]+)'?!([A-Z]+\d+(?::[A-Z]+\d+)?)")
NAMED_RANGE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]+)\b(?!\s*\()")
FUNCTION_RE = re.compile(r"\b([A-Z][A-Z0-9]+)\s*\(")


def parse_formula(formula: str) -> dict:
    if not formula or not formula.startswith("="):
        return {}

    expr = formula[1:]
    functions_used = []
    categories = set()

    for match in FUNCTION_RE.finditer(expr.upper()):
        fn = match.group(1)
        if fn in FUNCTION_FLAT:
            functions_used.append(fn)
            categories.add(FUNCTION_FLAT[fn])

    cross_refs = []
    for match in CROSS_SHEET_RE.finditer(expr):
        cross_refs.append({"sheet": match.group(1), "range": match.group(2)})

    is_array_formula = formula.startswith("{=")
    has_volatile = any(f in expr.upper() for f in ["TODAY(", "NOW(", "RAND(", "INDIRECT(", "OFFSET("])

    complexity = "simple"
    fn_count = len(set(functions_used))
    if fn_count >= 5 or cross_refs:
        complexity = "complex"
    elif fn_count >= 2:
        complexity = "medium"

    return {
        "formula": formula,
        "functions": list(set(functions_used)),
        "categories": list(categories),
        "cross_sheet_refs": cross_refs,
        "is_array": is_array_formula,
        "is_volatile": has_volatile,
        "complexity": complexity,
        "has_cross_sheet": len(cross_refs) > 0,
    }


def extract_formula_map(sheet_data: list[list[Any]], sheet_name: str) -> dict:
    formula_cells = []
    formula_categories: dict[str, int] = {}
    cross_sheet_deps: set[str] = set()

    for row_idx, row in enumerate(sheet_data):
        for col_idx, cell in enumerate(row):
            if isinstance(cell, str) and cell.startswith("="):
                parsed = parse_formula(cell)
                cell_ref = f"{_col_letter(col_idx)}{row_idx + 1}"
                formula_cells.append({
                    "cell": cell_ref,
                    "row": row_idx,
                    "col": col_idx,
                    **parsed,
                })
                for cat in parsed.get("categories", []):
                    formula_categories[cat] = formula_categories.get(cat, 0) + 1
                for ref in parsed.get("cross_sheet_refs", []):
                    cross_sheet_deps.add(ref["sheet"])

    return {
        "sheet": sheet_name,
        "formula_count": len(formula_cells),
        "formula_cells": formula_cells,
        "categories": formula_categories,
        "cross_sheet_dependencies": list(cross_sheet_deps),
        "has_financial": "financial" in formula_categories,
        "has_lookup": "lookup" in formula_categories,
        "has_array": any(fc.get("is_array") for fc in formula_cells),
        "has_volatile": any(fc.get("is_volatile") for fc in formula_cells),
        "complexity_distribution": _complexity_dist(formula_cells),
    }


def _col_letter(idx: int) -> str:
    result = ""
    idx += 1
    while idx:
        idx, remainder = divmod(idx - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _complexity_dist(cells: list) -> dict:
    dist: dict[str, int] = {}
    for c in cells:
        k = c.get("complexity", "simple")
        dist[k] = dist.get(k, 0) + 1
    return dist
