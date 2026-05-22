import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.schemas import ImportRequest, MappingRequest
from app.core.config import settings
from app.core.db import execute
from app.modules.excel_analyzer import analyze_workbook
from app.modules.ingestion import pipeline
from app.services import jobs, preview

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED = {".xlsx", ".xlsm", ".xls", ".xlsb", ".ods", ".csv", ".tsv"}


def _stored_path(upload_id: str) -> Path:
    matches = list(settings.uploads_dir.glob(f"{upload_id}.*"))
    if not matches:
        raise HTTPException(404, "upload_id no encontrado o expirado")
    return matches[0]


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """Paso 1 · Detectar estructura — stores the file, returns full analysis."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"Formato no soportado: {ext}. Permitidos: {sorted(ALLOWED)}")
    body = await file.read()
    if len(body) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Archivo supera {settings.max_upload_mb} MB")

    settings.ensure_dirs()
    upload_id = uuid.uuid4().hex
    dest = settings.uploads_dir / f"{upload_id}{ext}"
    dest.write_bytes(body)

    try:
        analysis = analyze_workbook(str(dest))
    except Exception as exc:  # noqa: BLE001
        dest.unlink(missing_ok=True)
        raise HTTPException(422, f"No se pudo analizar el archivo: {exc}")

    return {"upload_id": upload_id, "filename": file.filename, "analysis": analysis}


@router.post("/preview-mapping")
async def preview_mapping(req: MappingRequest):
    """Paso 2 · Mapear columnas — live preview with inline validation."""
    path = _stored_path(req.upload_id)
    return preview.preview_mapping(str(path), req.mapping, req.header_rows)


@router.post("/import")
async def start_import(req: ImportRequest):
    """Paso 3 · Confirmar e importar — kicks off the async pipeline."""
    path = _stored_path(req.upload_id)
    ingestion_id = uuid.uuid4().hex
    execute(
        "INSERT INTO ingestions (id, filename, period, source, status) VALUES (?,?,?,?,?)",
        [ingestion_id, path.name, req.period, "excel_historico", "pending"],
    )
    job_id = jobs.create_job("import")
    jobs.run_async(
        job_id,
        lambda jid: pipeline.run_import(
            ingestion_id, str(path), req.mapping, req.period, req.header_rows, jid
        ),
    )
    return {"job_id": job_id, "ingestion_id": ingestion_id, "status": "pending"}
