"""Excel Estructurador — FastAPI entry point.

Self-hosted app to turn messy Excels into clean structured data: upload &
preview wizard, configurable business schema, manual capture form, and a
unified explorer with source tracking. DuckDB + Parquet, no external services.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import get_conn
from app.api.routes import dashboard, ingestions, jobs, records, schema, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    get_conn()  # initialize DuckDB + tables
    yield


app = FastAPI(title="Excel Estructurador", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "excel-estructurador"}


for r in (upload, jobs, records, dashboard, schema, ingestions):
    app.include_router(r.router)
