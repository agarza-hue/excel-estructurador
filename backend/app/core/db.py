"""DuckDB access. Single embedded file, one shared connection serialized by a
lock (DuckDB is single-writer; import jobs run on worker threads, so every
write goes through `tx()`).

The master `records` table keeps a fixed set of system columns and stores the
configurable business fields in a JSON column — so editing the business schema
never requires an ALTER TABLE.
"""
import threading
from contextlib import contextmanager

import duckdb

from .config import settings

_conn: duckdb.DuckDBPyConnection | None = None
_lock = threading.RLock()

SCHEMA_SQL = """
INSTALL json; LOAD json;

CREATE SEQUENCE IF NOT EXISTS records_id_seq START 1;

-- NOTE: no PRIMARY KEY on _id. DuckDB UPDATEs (e.g. soft-delete _active) on a
-- table with a PK index falsely raise "duplicate key"; the sequence already
-- guarantees uniqueness, so we don't need the enforced constraint.
CREATE TABLE IF NOT EXISTS records (
    _id          BIGINT  DEFAULT nextval('records_id_seq'),
    _source      VARCHAR NOT NULL,                 -- excel_historico | web_form | api
    _period      VARCHAR,                          -- Q1_2025 ...
    _ingestion_id VARCHAR,                          -- FK-ish to ingestions.id
    _created_at  TIMESTAMP DEFAULT now(),
    _active      BOOLEAN DEFAULT TRUE,
    data         JSON    NOT NULL                  -- business fields
);

CREATE TABLE IF NOT EXISTS ingestions (
    id            VARCHAR,
    filename      VARCHAR,
    period        VARCHAR,
    source        VARCHAR DEFAULT 'excel_historico',
    status        VARCHAR DEFAULT 'pending',       -- pending|running|done|failed
    rows_total    INTEGER DEFAULT 0,
    rows_imported INTEGER DEFAULT 0,
    rows_ignored  INTEGER DEFAULT 0,
    rows_warning  INTEGER DEFAULT 0,
    warnings      JSON,
    raw_paths     JSON,
    error         VARCHAR,
    reverted      BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMP DEFAULT now()
);
"""


def get_conn() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        with _lock:
            if _conn is None:
                settings.ensure_dirs()
                _conn = duckdb.connect(str(settings.db_path))
                _conn.execute(SCHEMA_SQL)
    return _conn


@contextmanager
def tx():
    """Serialize access to the single connection across threads."""
    conn = get_conn()
    with _lock:
        yield conn


def query(sql: str, params: list | None = None) -> list[dict]:
    with tx() as conn:
        cur = conn.execute(sql, params or [])
        cols = [d[0] for d in cur.description] if cur.description else []
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def execute(sql: str, params: list | None = None) -> None:
    with tx() as conn:
        conn.execute(sql, params or [])
