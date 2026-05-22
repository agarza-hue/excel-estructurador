"""Paso 2 of the wizard: given a proposed column mapping, show how the data
would land — with inline per-cell validation warnings — without importing."""
from app.modules.excel_analyzer.file_loader import normalize_to_xlsx
from app.modules.ingestion.pipeline import IGNORE, extract_sheet_rows
from app.services.coerce import coerce_value
from app.services.schema_store import load_schema

PREVIEW_ROWS = 25


def preview_mapping(file_path: str, mapping: dict, header_rows: dict | None = None) -> dict:
    schema = load_schema()
    field_by_name = {f.name: f for f in schema.fields}
    header_rows = header_rows or {}
    work_path, _ = normalize_to_xlsx(file_path)

    sheets_out = []
    for sheet_name, col_map in mapping.items():
        headers, data_rows = extract_sheet_rows(work_path, sheet_name, header_rows.get(sheet_name))
        if not headers:
            continue
        active = {col: fld for col, fld in col_map.items()
                  if fld and fld != IGNORE and fld in field_by_name}
        col_index = {h: i for i, h in enumerate(headers)}
        target_fields = list(dict.fromkeys(active.values()))

        rows, warn_count = [], 0
        for row in data_rows[:PREVIEW_ROWS]:
            mapped, warns = {}, {}
            for col, field_name in active.items():
                idx = col_index.get(col)
                raw_val = row[idx] if idx is not None and idx < len(row) else None
                value, warn = coerce_value(field_by_name[field_name], raw_val)
                mapped[field_name] = value
                if warn:
                    warns[field_name] = warn
                    warn_count += 1
            rows.append({"values": mapped, "warnings": warns})

        sheets_out.append({
            "sheet_name": sheet_name,
            "target_fields": [
                {"name": f, "label": field_by_name[f].label, "type": field_by_name[f].type}
                for f in target_fields
            ],
            "rows": rows,
            "warning_count": warn_count,
            "preview_row_count": len(rows),
        })
    return {"sheets": sheets_out}
