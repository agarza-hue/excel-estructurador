"""Master records: insert (from form or import) and query (explorer + export)."""
import json
from typing import Any

from app.core.db import query, tx

SOURCE_BADGES = {
    "excel_historico": "gris",
    "web_form": "verde",
    "api": "azul",
}


def insert_record(data: dict, source: str, period: str | None = None,
                  ingestion_id: str | None = None) -> int:
    with tx() as conn:
        row = conn.execute(
            """INSERT INTO records (_source, _period, _ingestion_id, data)
               VALUES (?, ?, ?, ?) RETURNING _id""",
            [source, period, ingestion_id, json.dumps(data, default=str)],
        ).fetchone()
        return row[0]


def insert_many(rows: list[dict], source: str, period: str | None,
                ingestion_id: str | None) -> int:
    with tx() as conn:
        conn.executemany(
            """INSERT INTO records (_source, _period, _ingestion_id, data)
               VALUES (?, ?, ?, ?)""",
            [[source, period, ingestion_id, json.dumps(r, default=str)] for r in rows],
        )
    return len(rows)


def _build_filters(period, source, from_date, to_date, search) -> tuple[str, list]:
    clauses = ["_active = TRUE"]
    params: list[Any] = []
    if period:
        clauses.append("_period = ?"); params.append(period)
    if source:
        clauses.append("_source = ?"); params.append(source)
    if from_date:
        clauses.append("json_extract_string(data, '$.fecha') >= ?"); params.append(from_date)
    if to_date:
        clauses.append("json_extract_string(data, '$.fecha') <= ?"); params.append(to_date)
    if search:
        clauses.append("CAST(data AS VARCHAR) ILIKE ?"); params.append(f"%{search}%")
    return " AND ".join(clauses), params


def list_records(period=None, source=None, from_date=None, to_date=None,
                 search=None, limit=50, offset=0) -> dict:
    where, params = _build_filters(period, source, from_date, to_date, search)
    total = query(f"SELECT count(*) AS n FROM records WHERE {where}", params)[0]["n"]
    rows = query(
        f"""SELECT _id, _source, _period, _ingestion_id, _created_at, data
            FROM records WHERE {where}
            ORDER BY _id DESC LIMIT ? OFFSET ?""",
        params + [limit, offset],
    )
    breakdown = {
        r["_source"]: r["n"]
        for r in query(
            f"SELECT _source, count(*) AS n FROM records WHERE {where} GROUP BY _source",
            params,
        )
    }
    items = [_hydrate(r) for r in rows]
    return {"total": total, "items": items, "breakdown_by_source": breakdown,
            "limit": limit, "offset": offset}


def all_filtered(period=None, source=None, from_date=None, to_date=None,
                 search=None) -> list[dict]:
    where, params = _build_filters(period, source, from_date, to_date, search)
    rows = query(
        f"""SELECT _id, _source, _period, _created_at, data
            FROM records WHERE {where} ORDER BY _id DESC""",
        params,
    )
    return [_hydrate(r) for r in rows]


def recent_form_records(limit: int = 10) -> list[dict]:
    rows = query(
        """SELECT _id, _source, _period, _created_at, data
           FROM records WHERE _source = 'web_form' AND _active = TRUE
           ORDER BY _id DESC LIMIT ?""",
        [limit],
    )
    return [_hydrate(r) for r in rows]


def _hydrate(r: dict) -> dict:
    data = r.get("data")
    fields = json.loads(data) if isinstance(data, str) else (data or {})
    return {
        "_id": r["_id"],
        "_source": r["_source"],
        "_source_badge": SOURCE_BADGES.get(r["_source"], "gris"),
        "_period": r.get("_period"),
        "_created_at": str(r.get("_created_at")),
        **fields,
    }
