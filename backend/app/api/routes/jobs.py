from fastapi import APIRouter, HTTPException

from app.services import jobs

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(404, "job no encontrado")
    return job
