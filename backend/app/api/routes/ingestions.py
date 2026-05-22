import json

from fastapi import APIRouter, HTTPException

from app.core.db import query
from app.modules.ingestion import pipeline

router = APIRouter(prefix="/api/ingestions", tags=["ingestions"])


def _hydrate(r: dict) -> dict:
    for k in ("warnings", "raw_paths"):
        v = r.get(k)
        r[k] = json.loads(v) if isinstance(v, str) else (v or [])
    r["created_at"] = str(r.get("created_at"))
    return r


@router.get("")
async def list_ingestions():
    rows = query(
        """SELECT id, filename, period, source, status, rows_total, rows_imported,
                  rows_ignored, rows_warning, warnings, raw_paths, error, reverted, created_at
           FROM ingestions ORDER BY created_at DESC"""
    )
    return {"items": [_hydrate(r) for r in rows]}


@router.delete("/{ingestion_id}")
async def revert(ingestion_id: str):
    """Soft delete — marks records inactive, keeps Parquet on disk."""
    found = query("SELECT id, reverted FROM ingestions WHERE id=?", [ingestion_id])
    if not found:
        raise HTTPException(404, "Ingesta no encontrada")
    if found[0]["reverted"]:
        raise HTTPException(409, "La ingesta ya fue revertida")
    n = pipeline.revert_ingestion(ingestion_id)
    return {"ingestion_id": ingestion_id, "records_deactivated": n, "status": "reverted"}
