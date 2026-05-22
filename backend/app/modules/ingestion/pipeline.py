"""Import pipeline: parse → raw landing (Parquet) → transform (mapping +
coercion) → master (DuckDB records). Soft-delete on revert keeps the raw
Parquet intact, per the spec."""
import json
from pathlib import Path

import openpyxl
import pandas as pd

from app.core.config import settings
from app.core.db import execute, query, tx
from app.modules.excel_analyzer.file_loader import normalize_to_xlsx
from app.modules.excel_analyzer.structure_detector import detect_header_row, sanitize_column_name
from app.services import jobs, records
from app.services.coerce import coerce_value
from app.services.schema_store import load_schema

IGNORE = "__ignore__"


def extract_sheet_rows(path: str, sheet_name: str, header_row_idx: int | None) -> tuple[list[str], list[list]]:
    """Return (sanitized_headers, data_rows) for one sheet — header sanitization
    mirrors the analyzer so mapping keys line up exactly."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet_name]
    raw = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()
    while raw and all(c is None or str(c).strip() == "" for c in raw[-1]):
        raw.pop()
    if not raw:
        return [], []
    hdr = header_row_idx if header_row_idx is not None else detect_header_row(raw)

    header_cells = raw[hdr]
    last = max((i for i, c in enumerate(header_cells) if c is not None and str(c).strip()), default=-1)
    header_cells = header_cells[: last + 1]
    seen: dict[str, int] = {}
    headers: list[str] = []
    for cell in header_cells:
        name = sanitize_column_name(str(cell) if cell is not None else "")
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        headers.append(name)
    return headers, raw[hdr + 1:]


def land_raw(ingestion_id: str, sheet_name: str, headers: list[str], data_rows: list[list]) -> str:
    """Write the raw parsed sheet to Parquet (raw landing zone)."""
    out_dir = settings.raw_dir / ingestion_id
    out_dir.mkdir(parents=True, exist_ok=True)
    width = len(headers)
    norm = [(r + [None] * width)[:width] for r in data_rows]
    df = pd.DataFrame(norm, columns=headers)
    out_path = out_dir / f"{sanitize_column_name(sheet_name) or 'sheet'}.parquet"
    df.to_parquet(out_path, index=False)
    return str(out_path)


def run_import(ingestion_id: str, file_path: str, mapping: dict, period: str | None,
               header_rows: dict[str, int] | None = None, job_id: str | None = None) -> dict:
    """mapping: { sheet_name: { excel_col: schema_field | "__ignore__" } }"""
    schema = load_schema()
    field_by_name = {f.name: f for f in schema.fields}
    header_rows = header_rows or {}

    work_path, converted = normalize_to_xlsx(file_path)
    raw_paths, all_records, warnings = [], [], []
    rows_total = rows_imported = rows_ignored = rows_warning = 0

    execute("UPDATE ingestions SET status='running' WHERE id=?", [ingestion_id])

    try:
        for sheet_name, col_map in mapping.items():
            if job_id:
                jobs.log(job_id, f"Procesando hoja '{sheet_name}'")
            headers, data_rows = extract_sheet_rows(work_path, sheet_name, header_rows.get(sheet_name))
            if not headers:
                continue
            raw_paths.append(land_raw(ingestion_id, sheet_name, headers, data_rows))

            active = {col: fld for col, fld in col_map.items()
                      if fld and fld != IGNORE and fld in field_by_name}
            if not active:
                # Sheet included but nothing mapped to it — importing its rows would
                # produce empty records. Skip it (raw is already landed) and surface why.
                msg = f"[{sheet_name}] hoja incluida sin columnas mapeadas: omitida (0 filas importadas)"
                warnings.append(msg)
                if job_id:
                    jobs.log(job_id, msg, "warn")
                continue
            col_index = {h: i for i, h in enumerate(headers)}

            for r_i, row in enumerate(data_rows):
                rows_total += 1
                if all(c is None or str(c).strip() == "" for c in row):
                    rows_ignored += 1
                    continue
                rec, row_warn = {}, []
                for col, field_name in active.items():
                    idx = col_index.get(col)
                    raw_val = row[idx] if idx is not None and idx < len(row) else None
                    value, warn = coerce_value(field_by_name[field_name], raw_val)
                    rec[field_name] = value
                    if warn:
                        row_warn.append(warn)
                # A row whose mapped cells are all empty yields a meaningless record —
                # ignore it instead of inserting a blank row.
                if not any(v is not None and str(v).strip() != "" for v in rec.values()):
                    rows_ignored += 1
                    continue
                if row_warn:
                    rows_warning += 1
                    warnings.extend(f"[{sheet_name}:fila {r_i + 2}] {w}" for w in row_warn[:3])
                all_records.append(rec)
                if job_id and rows_total % 200 == 0:
                    jobs.progress(job_id, rows_total)

        if all_records:
            records.insert_many(all_records, "excel_historico", period, ingestion_id)
        rows_imported = len(all_records)

        execute(
            """UPDATE ingestions SET status='done', rows_total=?, rows_imported=?,
               rows_ignored=?, rows_warning=?, warnings=?, raw_paths=? WHERE id=?""",
            [rows_total, rows_imported, rows_ignored, rows_warning,
             json.dumps(warnings[:100]), json.dumps(raw_paths), ingestion_id],
        )
        if job_id:
            jobs.progress(job_id, rows_total, rows_total)
        return {"ingestion_id": ingestion_id, "rows_total": rows_total,
                "rows_imported": rows_imported, "rows_ignored": rows_ignored,
                "rows_warning": rows_warning, "warnings": warnings[:100]}
    except Exception as exc:
        execute("UPDATE ingestions SET status='failed', error=? WHERE id=?",
                [str(exc), ingestion_id])
        raise
    finally:
        if converted:
            Path(work_path).unlink(missing_ok=True)


def revert_ingestion(ingestion_id: str) -> int:
    """Soft delete: mark records inactive, flag ingestion. Parquet stays."""
    with tx() as conn:
        n = conn.execute(
            "UPDATE records SET _active=FALSE WHERE _ingestion_id=? AND _active=TRUE RETURNING _id",
            [ingestion_id],
        ).fetchall()
        conn.execute("UPDATE ingestions SET reverted=TRUE WHERE id=?", [ingestion_id])
    return len(n)
