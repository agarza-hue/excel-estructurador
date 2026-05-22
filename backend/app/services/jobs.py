"""In-process job registry. Replaces the original project's Celery+Redis with a
thread per import — appropriate for a single-process self-hosted app. State is
polled via GET /api/jobs/{id} (the wizard's Paso 3 progress bar)."""
import threading
import time
import traceback
import uuid
from typing import Callable

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def create_job(kind: str, total: int = 0) -> str:
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = {
            "id": job_id, "kind": kind, "status": "pending",
            "rows_total": total, "rows_processed": 0,
            "logs": [], "result": None, "error": None,
            "started_at": time.time(),
        }
    return job_id


def _update(job_id: str, **fields):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)


def log(job_id: str, msg: str, level: str = "info"):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["logs"].append({"t": round(time.time(), 3), "level": level, "msg": msg})


def progress(job_id: str, processed: int, total: int | None = None):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["rows_processed"] = processed
            if total is not None:
                _jobs[job_id]["rows_total"] = total


def get_job(job_id: str) -> dict | None:
    with _lock:
        return dict(_jobs[job_id]) if job_id in _jobs else None


def run_async(job_id: str, target: Callable[[str], dict]):
    """Run target(job_id) on a worker thread; capture result/exception."""
    def _runner():
        _update(job_id, status="running")
        try:
            result = target(job_id)
            _update(job_id, status="done", result=result)
            log(job_id, "Importación completada", "success")
        except Exception as exc:  # noqa: BLE001
            _update(job_id, status="failed", error=str(exc))
            log(job_id, f"Error: {exc}", "error")
            traceback.print_exc()

    threading.Thread(target=_runner, daemon=True).start()
