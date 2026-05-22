# API Contract — Excel Estructurador backend

Base URL in dev: backend runs at `http://localhost:8077`. The Vite frontend
should proxy `/api` → `http://localhost:8077`. All bodies are JSON unless noted.

## Field types (business schema)
`text | number | currency | date | boolean | select`

## Source badge colors
`excel_historico` → gris (gray) · `web_form` → verde (green) · `api` → azul (blue)

---

### GET /api/health
→ `{ status, service }`

### POST /api/upload/analyze   (multipart, field name `file`)
→ `{ upload_id, filename, analysis }`
- `analysis.workbook_structure`: `{ filename, sheet_count, sheet_names[], total_rows, has_formulas, formula_count, has_pivot_tables, has_hidden_sheets, sheets[] }`
- `sheets[]` item: `{ index, sheet_name, is_hidden, row_count, col_count, header_row, structure_type, structure_label, structure_reasons[], has_merged_cells, has_formulas, formula_count, columns_meta[], sample_data[] }`
  - `structure_type` ∈ `clean | multi_header | cross_tab | multi_section | empty`
  - `structure_label` is the Spanish label ("tabla limpia", "multi-header", "cross-tab", "multi-sección")
  - `sample_data[]`: list of `{ columnName: value|null }` (first ~20 rows)
- `columns_meta[]` item: `{ name, index, type, sql_type, sample_values[], null_rate, is_unique }`

### POST /api/upload/preview-mapping
body `{ upload_id, mapping, header_rows? }`
- `mapping`: `{ [sheetName]: { [excelColumnName]: targetFieldName | "__ignore__" } }`
- `header_rows`: `{ [sheetName]: number }` (0-based override, optional)
→ `{ sheets: [ { sheet_name, target_fields: [{name,label,type}], rows: [{ values: {field: val}, warnings: {field: msg} }], warning_count, preview_row_count } ] }`

### POST /api/upload/import
body `{ upload_id, mapping, period?, header_rows? }`
→ `{ job_id, ingestion_id, status }`

### GET /api/jobs/{job_id}
→ `{ id, kind, status, rows_total, rows_processed, logs: [{t,level,msg}], result, error }`
- `status` ∈ `pending | running | done | failed`
- `result` (when done): `{ ingestion_id, rows_total, rows_imported, rows_ignored, rows_warning, warnings[] }`

### POST /api/records
body `{ data: { [field]: value }, period? }`
→ 200 `{ _id, status }`   |   422 `{ detail: { message, warnings: string[] } }`

### GET /api/records?period&source&from_date&to_date&search&limit&offset
→ `{ total, items: [{ _id, _source, _source_badge, _period, _created_at, ...businessFields }], breakdown_by_source: {src: n}, limit, offset }`

### GET /api/records/recent-form  → `{ items: [...] }` (last 10 web_form)

### GET /api/records/export?format=csv|xlsx&period&source&from_date&to_date&search
→ file download (Content-Disposition attachment)

### GET /api/dashboard/stats
→ `{ total, historico, nuevos, by_source: {src:n}, source_badges, by_period: [{period, n}], recent_ingestions: [{id, filename, period, status, rows_imported, created_at, reverted}] }`

### GET /api/schema  /  PUT /api/schema
schema shape: `{ fields: [{ name, label, type, required, options: string[] }], version }`
- PUT body is the full schema; server bumps `version`.

### GET /api/ingestions
→ `{ items: [{ id, filename, period, source, status, rows_total, rows_imported, rows_ignored, rows_warning, warnings[], raw_paths[], error, reverted, created_at }] }`

### DELETE /api/ingestions/{id}   (soft delete / revert)
→ 200 `{ ingestion_id, records_deactivated, status }`  |  404  |  409 (already reverted)
