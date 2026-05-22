import io

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.schemas import RecordCreate
from app.services import records
from app.services.coerce import coerce_value
from app.services.schema_store import load_schema

router = APIRouter(prefix="/api/records", tags=["records"])


@router.post("")
async def create_record(req: RecordCreate):
    """Pantalla 3 — capture form. Validates against the business schema."""
    schema = load_schema()
    clean, warnings = {}, []
    for field in schema.fields:
        value, warn = coerce_value(field, req.data.get(field.name))
        clean[field.name] = value
        if warn:
            warnings.append(warn)
    if warnings:
        raise HTTPException(422, {"message": "Validación fallida", "warnings": warnings})
    rec_id = records.insert_record(clean, "web_form", req.period)
    return {"_id": rec_id, "status": "created"}


@router.get("")
async def list_records(
    period: str | None = None, source: str | None = None,
    from_date: str | None = None, to_date: str | None = None,
    search: str | None = None,
    limit: int = Query(50, le=500), offset: int = 0,
):
    return records.list_records(period, source, from_date, to_date, search, limit, offset)


@router.get("/recent-form")
async def recent_form():
    return {"items": records.recent_form_records(10)}


@router.get("/export")
async def export(
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    period: str | None = None, source: str | None = None,
    from_date: str | None = None, to_date: str | None = None,
    search: str | None = None,
):
    rows = records.all_filtered(period, source, from_date, to_date, search)
    if not rows:
        raise HTTPException(404, "No hay registros para exportar con esos filtros")
    df = pd.DataFrame(rows).drop(columns=["_source_badge"], errors="ignore")

    if format == "csv":
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return StreamingResponse(
            iter([buf.getvalue()]), media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=registros.csv"},
        )
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="registros")
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=registros.xlsx"},
    )
