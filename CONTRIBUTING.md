# Contributing to Excel Estructurador

Thanks for your interest in contributing! This guide covers local setup, the
checks CI runs, and the conventions to follow so your PR lands smoothly.

## Project layout

- `backend/` — FastAPI app (Python 3.12), DuckDB + Parquet. Tests in `backend/tests/`.
- `frontend/` — React + Vite + TypeScript + Tailwind SPA.
- `API_CONTRACT.md` — the HTTP contract the frontend consumes. **Keep it in
  sync** whenever you change a request/response shape.
- `README.md` — architecture and run instructions.

## Prerequisites

- Python **3.12+**
- Node **20+** (CI builds on 22)

## Backend setup

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt      # app deps + pytest/httpx
uvicorn app.main:app --reload --port 8077 # API at http://localhost:8077/docs
```

Run the test suite (this is what the `backend-tests` workflow runs):

```bash
cd backend && . .venv/bin/activate
pytest -q
```

All app data (DuckDB file, raw Parquet, uploads, `schema.json`) lives under
`backend/data/` and is gitignored — safe to delete to reset state. Tests use an
isolated temp data dir, so they never touch your dev database.

## Frontend setup

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, proxies /api -> :8077
```

Build + type-check (this is what the `frontend-build` workflow runs):

```bash
cd frontend
npm run build    # tsc -b && vite build
```

## Before you open a PR

Run the same checks CI will:

- **Backend change** → `pytest -q` passes, and add/extend a test for the
  behavior you changed (the suite is end-to-end against the real API).
- **Frontend change** → `npm run build` passes cleanly (no TS errors).
- **API change** → update `API_CONTRACT.md` and the corresponding types in
  `frontend/src/lib/types.ts`.

CI (`backend-tests`, `frontend-build`) is path-filtered, so only the affected
half runs — but both must be green on a PR that touches both.

## Conventions

- **Python**: match the existing style — type hints, small focused functions,
  thin route handlers that delegate to `app/services/` and `app/modules/`.
- **TypeScript**: `strict` is on; avoid `any`. All HTTP calls go through
  `frontend/src/lib/api.ts`, all response shapes through `types.ts`.
- **Commits**: short imperative subject with a type prefix
  (`feat:`, `fix:`, `docs:`, `ci:`, `refactor:`, `test:`). Explain the *why* in
  the body when it isn't obvious.
- **Branches**: work on a feature branch and open a PR against `master`. Don't
  commit directly to `master`.

## Reporting bugs / proposing features

Open a GitHub issue describing the behavior you saw vs. expected, with steps to
reproduce. For Excel-parsing bugs, attaching a small sample workbook (with any
sensitive data removed) helps enormously.

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
