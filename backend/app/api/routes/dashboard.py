from fastapi import APIRouter

from app.core.db import query
from app.services.records import SOURCE_BADGES

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def stats():
    total = query("SELECT count(*) AS n FROM records WHERE _active=TRUE")[0]["n"]
    by_source = {
        r["_source"]: r["n"]
        for r in query(
            "SELECT _source, count(*) AS n FROM records WHERE _active=TRUE GROUP BY _source"
        )
    }
    by_period = query(
        """SELECT coalesce(_period, 'sin_periodo') AS period, count(*) AS n
           FROM records WHERE _active=TRUE GROUP BY 1 ORDER BY 1"""
    )
    recent = query(
        """SELECT id, filename, period, status, rows_imported, created_at, reverted
           FROM ingestions ORDER BY created_at DESC LIMIT 8"""
    )
    historico = by_source.get("excel_historico", 0)
    nuevos = by_source.get("web_form", 0) + by_source.get("api", 0)
    return {
        "total": total,
        "historico": historico,
        "nuevos": nuevos,
        "by_source": by_source,
        "source_badges": SOURCE_BADGES,
        "by_period": by_period,
        "recent_ingestions": [{**r, "created_at": str(r["created_at"])} for r in recent],
    }
