# Excel Estructurador

App web self-hosted para convertir Exceles desordenados en datos estructurados.
Un usuario no técnico sube cualquier Excel, ve cómo quedó parseado, corrige el
mapeo de columnas, e importa el resultado a un almacén unificado — o captura
datos nuevos desde un formulario una vez que deja el Excel.

## Stack

| Capa       | Tech                                                  |
| ---------- | ----------------------------------------------------- |
| Frontend   | React + Vite + TypeScript + Tailwind CSS              |
| Backend    | FastAPI (Python 3.12)                                 |
| Parser     | openpyxl + pandas                                     |
| Base datos | DuckDB (archivo local, sin servidor)                  |
| Raw landing| Parquet (`backend/data/raw/<ingestion_id>/*.parquet`) |
| Jobs       | hilos in-process (sin Celery/Redis)                   |

> El motor de análisis de Excel (detección de estructura, inferencia de tipos,
> parsing de fórmulas, scoring de calidad) está **portado del proyecto
> `excel_platform`** — es código probado y puro-python sobre openpyxl. Aquí se
> reusa sin su andamiaje pesado (Postgres/Celery/MinIO/IA) y se le añade un
> clasificador estructural que produce las 4 categorías del wizard.

## Estructura

```
backend/
├── app/
│   ├── main.py                FastAPI entrypoint
│   ├── core/                  config + DuckDB
│   ├── modules/
│   │   ├── excel_analyzer/    PORTADO de excel_platform + structural_classifier
│   │   └── ingestion/         pipeline parse→raw→transform→master + revert
│   ├── services/              schema, records, coerce, preview, jobs
│   └── api/routes/            upload, jobs, records, dashboard, schema, ingestions
├── tests/                     pytest e2e (6 tests)
└── requirements.txt
frontend/                      Vite + React + TS (5 pantallas)
API_CONTRACT.md                contrato HTTP que consume el frontend
```

## Cómo correr

### Backend
```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8077
# docs: http://localhost:8077/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxya /api → :8077)
```

### Tests del backend
```bash
cd backend && . .venv/bin/activate && python -m pytest -q
```

## Las 5 pantallas

1. **Dashboard** — contadores históricos vs nuevos, últimas ingestas, gráfico por período.
2. **Upload & Preview** — wizard de 3 pasos: detectar estructura → mapear columnas (preview en vivo + validación inline) → confirmar e importar (progreso por polling).
3. **Captura** — formulario con los campos del schema configurable, validación en vivo, últimos 10 registros, importar CSV.
4. **Explorador** — tabla unificada (histórico + nuevos) con filtros, badge de `_source` por color, export CSV/Excel.
5. **Configuración** — editar el schema de negocio, ver ingestas, revertir (soft-delete que conserva el Parquet).

## Notas de diseño

- **Schema configurable** sin migraciones: los campos de negocio viven en una
  columna `data JSON` de la tabla `records`; editar el schema nunca hace ALTER.
- **`_source`** siempre presente: `excel_historico` (gris) · `web_form` (verde) · `api` (azul).
- **Revert = soft-delete**: marca `records._active=FALSE` y `ingestions.reverted=TRUE`;
  el Parquet del raw landing nunca se borra.
- El archivo subido se manda una sola vez (`/upload/analyze` devuelve `upload_id`);
  los pasos siguientes referencian ese id en lugar de reenviar el workbook.
