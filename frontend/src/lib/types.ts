export type FieldType = "text" | "number" | "currency" | "date" | "boolean" | "select";
export type StructureType = "clean" | "multi_header" | "cross_tab" | "multi_section" | "empty" | "dashboard";
export type JobStatus = "pending" | "running" | "done" | "failed";
export type SourceType = "excel_historico" | "web_form" | "api";
export type SourceBadge = "gris" | "verde" | "azul" | string;
export type JsonValue = string | number | boolean | null;
export type RecordValue = JsonValue | undefined;

export interface HealthResponse {
  status: string;
  service: string;
}

export interface SchemaField {
  name: string;
  label: string;
  type: FieldType;
  required: boolean;
  options: string[];
}

export interface SchemaResponse {
  fields: SchemaField[];
  version: number;
}

export interface ColumnMeta {
  name: string;
  index: number;
  type: string;
  sql_type: string;
  sample_values: JsonValue[];
  null_rate: number;
  is_unique: boolean;
}

export interface SheetAnalysis {
  index: number;
  sheet_name: string;
  is_hidden: boolean;
  row_count: number;
  col_count: number;
  header_row: number;
  structure_type: StructureType;
  structure_label: string;
  structure_reasons: string[];
  has_merged_cells: boolean;
  has_formulas: boolean;
  formula_count: number;
  columns_meta: ColumnMeta[];
  sample_data: Record<string, JsonValue>[];
}

export interface WorkbookStructure {
  filename: string;
  sheet_count: number;
  sheet_names: string[];
  total_rows: number;
  has_formulas: boolean;
  formula_count: number;
  has_pivot_tables: boolean;
  has_hidden_sheets: boolean;
  sheets: SheetAnalysis[];
}

export interface AnalyzeUploadResponse {
  upload_id: string;
  filename: string;
  analysis: {
    workbook_structure: WorkbookStructure;
  };
}

export type SheetMapping = Record<string, string>;
export type UploadMapping = Record<string, SheetMapping>;
export type HeaderRows = Record<string, number>;

export interface PreviewTargetField {
  name: string;
  label: string;
  type: FieldType;
}

export interface PreviewRow {
  values: Record<string, JsonValue>;
  warnings: Record<string, string>;
}

export interface PreviewSheet {
  sheet_name: string;
  target_fields: PreviewTargetField[];
  rows: PreviewRow[];
  warning_count: number;
  preview_row_count: number;
}

export interface PreviewMappingResponse {
  sheets: PreviewSheet[];
}

export interface ImportResponse {
  job_id: string;
  ingestion_id: string;
  status: JobStatus;
}

export interface JobLog {
  t: string;
  level: string;
  msg: string;
}

export interface JobResult {
  ingestion_id: string;
  rows_total: number;
  rows_imported: number;
  rows_ignored: number;
  rows_warning: number;
  warnings: string[];
}

export interface JobResponse {
  id: string;
  kind: string;
  status: JobStatus;
  rows_total: number;
  rows_processed: number;
  logs: JobLog[];
  result: JobResult | null;
  error: string | null;
}

export interface RecordCreateRequest {
  data: Record<string, RecordValue>;
  period?: string;
}

export interface RecordCreateResponse {
  _id: string;
  status: string;
}

export interface ApiValidationDetail {
  message: string;
  warnings: string[];
}

export interface ApiValidationError {
  detail: ApiValidationDetail;
}

export interface BusinessRecord {
  _id: string;
  _source: SourceType | string;
  _source_badge: SourceBadge;
  _period: string | null;
  _created_at: string;
  [field: string]: RecordValue;
}

export interface RecordsResponse {
  total: number;
  items: BusinessRecord[];
  breakdown_by_source: Record<string, number>;
  limit: number;
  offset: number;
}

export interface RecentFormResponse {
  items: BusinessRecord[];
}

export interface DashboardIngestion {
  id: string;
  filename: string;
  period: string | null;
  status: string;
  rows_imported: number;
  created_at: string;
  reverted: boolean;
}

export interface DashboardStats {
  total: number;
  historico: number;
  nuevos: number;
  by_source: Record<string, number>;
  source_badges: Record<string, SourceBadge>;
  by_period: { period: string; n: number }[];
  recent_ingestions: DashboardIngestion[];
}

export interface Ingestion {
  id: string;
  filename: string;
  period: string | null;
  source: string;
  status: string;
  rows_total: number;
  rows_imported: number;
  rows_ignored: number;
  rows_warning: number;
  warnings: string[];
  raw_paths: string[];
  error: string | null;
  reverted: boolean;
  created_at: string;
}

export interface IngestionsResponse {
  items: Ingestion[];
}

export interface RevertIngestionResponse {
  ingestion_id: string;
  records_deactivated: number;
  status: string;
}

export interface RecordsQuery {
  period?: string;
  source?: string;
  from_date?: string;
  to_date?: string;
  search?: string;
  limit?: number;
  offset?: number;
}
