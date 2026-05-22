"""End-to-end API tests against a throwaway data dir.

Covers the spec's core loop: analyze → preview → import (async job) → records →
dashboard → export → soft-delete revert, plus form validation.
"""
import os
import tempfile
import time

import pytest

# Point the app at an isolated data dir BEFORE importing it.
os.environ["XE_DATA_DIR"] = tempfile.mkdtemp(prefix="xe_test_")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SAMPLE = "/root/excel_platform/scripts/sample_empresa.xlsx"
client = TestClient(app)

VENTAS_MAP = {
    "Ventas": {"fecha": "fecha", "vendedor": "descripcion",
               "estatus": "categoria", "cantidad": "cantidad", "total": "monto"}
}


@pytest.fixture(scope="module")
def imported():
    with open(SAMPLE, "rb") as fh:
        r = client.post("/api/upload/analyze",
                        files={"file": ("sample.xlsx", fh,
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200, r.text
    upload_id = r.json()["upload_id"]

    r = client.post("/api/upload/import",
                    json={"upload_id": upload_id, "period": "Q1_2025", "mapping": VENTAS_MAP})
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    ingestion_id = r.json()["ingestion_id"]

    for _ in range(50):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            break
        time.sleep(0.1)
    assert job["status"] == "done", job
    assert job["result"]["rows_imported"] == 500
    return {"upload_id": upload_id, "ingestion_id": ingestion_id}


def _import_and_wait(upload_id, mapping, period="Q2_2025"):
    r = client.post("/api/upload/import",
                    json={"upload_id": upload_id, "period": period, "mapping": mapping})
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    for _ in range(50):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            break
        time.sleep(0.1)
    return job


def test_unmapped_sheet_imports_no_empty_records():
    """A sheet included with no mapped columns must be skipped (with a warning),
    not imported as blank records, while a mapped sheet imports normally."""
    with open(SAMPLE, "rb") as fh:
        upload_id = client.post("/api/upload/analyze", files={"file": ("s.xlsx", fh)}).json()["upload_id"]

    # Ventas fully mapped; Productos included but mapped to nothing.
    job = _import_and_wait(upload_id, {**VENTAS_MAP, "Productos": {}})
    assert job["status"] == "done", job
    res = job["result"]
    assert res["rows_imported"] == 500          # only Ventas — no blank Productos rows
    assert any("Productos" in w and "omitida" in w for w in res["warnings"])


def test_analyze_detects_sheets_and_structure():
    with open(SAMPLE, "rb") as fh:
        r = client.post("/api/upload/analyze", files={"file": ("s.xlsx", fh)})
    sheets = r.json()["analysis"]["workbook_structure"]["sheets"]
    assert {s["sheet_name"] for s in sheets} >= {"Ventas", "Productos"}
    assert all("structure_type" in s for s in sheets)


def test_preview_coerces_and_flags(imported):
    r = client.post("/api/upload/preview-mapping",
                    json={"upload_id": imported["upload_id"], "mapping": VENTAS_MAP})
    sheet = r.json()["sheets"][0]
    assert sheet["rows"][0]["values"]["fecha"].count("-") == 2  # ISO date
    assert isinstance(sheet["rows"][0]["values"]["monto"], (int, float))


def test_records_and_dashboard(imported):
    assert client.get("/api/records").json()["total"] >= 500
    stats = client.get("/api/dashboard/stats").json()
    assert stats["by_source"]["excel_historico"] >= 500
    assert any(p["period"] == "Q1_2025" for p in stats["by_period"])


def test_form_create_and_validation():
    ok = client.post("/api/records", json={
        "data": {"fecha": "15/03/2025", "descripcion": "manual", "monto": "1.250,50"},
        "period": "Q1_2025"})
    assert ok.status_code == 200
    bad = client.post("/api/records", json={"data": {"categoria": "x"}})
    assert bad.status_code == 422  # missing required fecha + descripcion


def test_export_csv(imported):
    r = client.get("/api/records/export", params={"format": "csv", "source": "excel_historico"})
    assert r.status_code == 200
    assert r.text.splitlines()[0].startswith("_id,_source")


def test_revert_soft_deletes(imported):
    before = client.get("/api/records").json()["total"]
    r = client.delete(f"/api/ingestions/{imported['ingestion_id']}")
    assert r.status_code == 200
    assert r.json()["records_deactivated"] == 500
    after = client.get("/api/records").json()["total"]
    assert after == before - 500
    # double revert is rejected
    assert client.delete(f"/api/ingestions/{imported['ingestion_id']}").status_code == 409
