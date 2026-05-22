import type {
  AnalyzeUploadResponse,
  HeaderRows,
  ImportResponse,
  IngestionsResponse,
  JobResponse,
  PreviewMappingResponse,
  RecordCreateRequest,
  RecordCreateResponse,
  RecordsQuery,
  RecordsResponse,
  RecentFormResponse,
  RevertIngestionResponse,
  SchemaResponse,
  UploadMapping
} from "./types";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(`API request failed with status ${status}`);
    this.status = status;
    this.body = body;
  }
}

const jsonHeaders = { "Content-Type": "application/json" };

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const body = await parseBody(response);
  if (!response.ok) {
    throw new ApiError(response.status, body);
  }
  return body as T;
}

function queryString(params: object): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if ((typeof value === "string" || typeof value === "number") && value !== "") search.set(key, String(value));
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export const api = {
  getStats: () => request<import("./types").DashboardStats>("/api/dashboard/stats"),
  getSchema: () => request<SchemaResponse>("/api/schema"),
  updateSchema: (schema: SchemaResponse) =>
    request<SchemaResponse>("/api/schema", {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify(schema)
    }),
  analyzeUpload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<AnalyzeUploadResponse>("/api/upload/analyze", {
      method: "POST",
      body: formData
    });
  },
  previewMapping: (upload_id: string, mapping: UploadMapping, header_rows?: HeaderRows) =>
    request<PreviewMappingResponse>("/api/upload/preview-mapping", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ upload_id, mapping, header_rows: header_rows ?? {} })
    }),
  importUpload: (upload_id: string, mapping: UploadMapping, period?: string, header_rows?: HeaderRows) =>
    request<ImportResponse>("/api/upload/import", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ upload_id, mapping, period: period || undefined, header_rows: header_rows ?? {} })
    }),
  getJob: (jobId: string) => request<JobResponse>(`/api/jobs/${jobId}`),
  createRecord: (payload: RecordCreateRequest) =>
    request<RecordCreateResponse>("/api/records", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload)
    }),
  getRecords: (params: RecordsQuery) => request<RecordsResponse>(`/api/records${queryString(params)}`),
  getRecentForm: () => request<RecentFormResponse>("/api/records/recent-form"),
  getIngestions: () => request<IngestionsResponse>("/api/ingestions"),
  revertIngestion: (id: string) =>
    request<RevertIngestionResponse>(`/api/ingestions/${id}`, {
      method: "DELETE"
    }),
  exportRecordsUrl: (format: "csv" | "xlsx", params: RecordsQuery) =>
    `/api/records/export${queryString({ ...params, format, limit: undefined, offset: undefined })}`
};
