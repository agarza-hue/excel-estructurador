import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { StructureBadge, StatusBadge } from "../components/Badge";
import { ErrorBlock, PageHeader, buttonPrimary, buttonSecondary, tableClass, tdClass, thClass } from "../components/State";
import { api } from "../lib/api";
import type {
  AnalyzeUploadResponse,
  HeaderRows,
  JobResponse,
  JsonValue,
  PreviewMappingResponse,
  SchemaResponse,
  SheetAnalysis,
  UploadMapping
} from "../lib/types";

const ignoreValue = "__ignore__";
const periodOptions = ["Q1_2025", "Q2_2025", "Q3_2025", "Q4_2025", "FY_2025"];

export default function UploadPage() {
  const [step, setStep] = useState(1);
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeUploadResponse | null>(null);
  const [included, setIncluded] = useState<Record<string, boolean>>({});
  const [mapping, setMapping] = useState<UploadMapping>({});
  const [headerRows, setHeaderRows] = useState<HeaderRows>({});
  const [preview, setPreview] = useState<PreviewMappingResponse | null>(null);
  const [period, setPeriod] = useState(periodOptions[0]);
  const [job, setJob] = useState<JobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const sheets = analysis?.analysis.workbook_structure.sheets ?? [];
  const includedSheets = useMemo(() => sheets.filter((sheet) => included[sheet.sheet_name]), [included, sheets]);

  useEffect(() => {
    api.getSchema().then(setSchema).catch(() => setError("No se pudo cargar el esquema."));
  }, []);

  useEffect(() => {
    if (!analysis || !schema || includedSheets.length === 0 || step !== 2) return;
    const handle = window.setTimeout(() => {
      api
        .previewMapping(analysis.upload_id, mappingForIncluded(mapping, includedSheets), headerRows)
        .then(setPreview)
        .catch(() => setError("No se pudo generar la vista previa del mapeo."));
    }, 400);
    return () => window.clearTimeout(handle);
  }, [analysis, headerRows, includedSheets, mapping, schema, step]);

  useEffect(() => {
    if (!job || (job.status !== "pending" && job.status !== "running")) return;
    const handle = window.setInterval(() => {
      api.getJob(job.id).then(setJob).catch(() => setError("No se pudo consultar el avance del trabajo."));
    }, 600);
    return () => window.clearInterval(handle);
  }, [job]);

  async function analyze(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const response = await api.analyzeUpload(file);
      const defaultIncluded: Record<string, boolean> = {};
      const defaultMapping: UploadMapping = {};
      const defaultHeaders: HeaderRows = {};
      response.analysis.workbook_structure.sheets.forEach((sheet) => {
        defaultIncluded[sheet.sheet_name] = sheet.row_count > 0 && !["empty", "dashboard"].includes(sheet.structure_type);
        defaultHeaders[sheet.sheet_name] = sheet.header_row;
        defaultMapping[sheet.sheet_name] = Object.fromEntries(sheet.columns_meta.map((column) => [column.name, ignoreValue]));
      });
      setAnalysis(response);
      setIncluded(defaultIncluded);
      setMapping(defaultMapping);
      setHeaderRows(defaultHeaders);
      setStep(1);
    } catch {
      setError("No se pudo analizar el archivo.");
    } finally {
      setBusy(false);
    }
  }

  function updateMapping(sheetName: string, columnName: string, target: string) {
    setMapping((current) => ({
      ...current,
      [sheetName]: { ...(current[sheetName] ?? {}), [columnName]: target }
    }));
  }

  async function startImport() {
    if (!analysis) return;
    setBusy(true);
    setError(null);
    try {
      const response = await api.importUpload(analysis.upload_id, mappingForIncluded(mapping, includedSheets), period, headerRows);
      setJob({ id: response.job_id, kind: "upload", status: response.status, rows_total: 0, rows_processed: 0, logs: [], result: null, error: null });
    } catch {
      setError("No se pudo iniciar la importación.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Importar histórico" subtitle="Analiza hojas, mapea columnas y ejecuta la ingesta controlada." />
      {error ? <div className="mb-4"><ErrorBlock message={error} /></div> : null}
      <StepIndicator step={step} />

      {step === 1 ? (
        <section className="space-y-5">
          <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
            <label className="block text-sm font-medium text-slate-700">
              Archivo Excel o CSV
              <input className="mt-2 block w-full" type="file" accept=".xlsx,.xls,.csv" onChange={analyze} disabled={busy} />
            </label>
            {busy ? <p className="mt-3 text-sm text-slate-500">Analizando archivo...</p> : null}
          </div>
          {analysis ? (
            <>
              <div className="grid gap-4">
                {sheets.map((sheet) => (
                  <SheetCard
                    key={sheet.sheet_name}
                    sheet={sheet}
                    included={Boolean(included[sheet.sheet_name])}
                    onIncluded={(value) => setIncluded((current) => ({ ...current, [sheet.sheet_name]: value }))}
                  />
                ))}
              </div>
              <div className="flex justify-end">
                <button className={buttonPrimary} disabled={includedSheets.length === 0} onClick={() => setStep(2)}>
                  Continuar al mapeo
                </button>
              </div>
            </>
          ) : null}
        </section>
      ) : null}

      {step === 2 && schema ? (
        <section className="space-y-5">
          {includedSheets.map((sheet) => (
            <MappingTable
              key={sheet.sheet_name}
              sheet={sheet}
              schema={schema}
              sheetMapping={mapping[sheet.sheet_name] ?? {}}
              preview={preview?.sheets.find((item) => item.sheet_name === sheet.sheet_name)}
              headerRow={headerRows[sheet.sheet_name] ?? sheet.header_row}
              onHeaderRow={(value) => setHeaderRows((current) => ({ ...current, [sheet.sheet_name]: value }))}
              onChange={(column, target) => updateMapping(sheet.sheet_name, column, target)}
            />
          ))}
          <div className="flex justify-between">
            <button className={buttonSecondary} onClick={() => setStep(1)}>Volver</button>
            <button className={buttonPrimary} onClick={() => setStep(3)}>Revisar importación</button>
          </div>
        </section>
      ) : null}

      {step === 3 ? (
        <section className="space-y-5">
          <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-950">Resumen</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <Summary label="Hojas incluidas" value={includedSheets.length} />
              <Summary label="Columnas mapeadas" value={countMapped(mappingForIncluded(mapping, includedSheets))} />
              <Summary label="Advertencias preview" value={preview?.sheets.reduce((sum, sheet) => sum + sheet.warning_count, 0) ?? 0} />
            </div>
            <label className="mt-5 block max-w-xs text-sm font-medium text-slate-700">
              Periodo
              <select className="mt-1 w-full" value={period} onChange={(event) => setPeriod(event.target.value)}>
                {periodOptions.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            <div className="mt-5 flex gap-2">
              <button className={buttonSecondary} onClick={() => setStep(2)}>Volver</button>
              <button className={buttonPrimary} onClick={startImport} disabled={busy || Boolean(job && job.status !== "failed")}>
                Importar
              </button>
            </div>
          </div>

          {job ? <JobProgress job={job} /> : null}
        </section>
      ) : null}
    </>
  );
}

function StepIndicator({ step }: { step: number }) {
  return (
    <div className="mb-6 grid gap-2 sm:grid-cols-3">
      {["Analizar", "Mapear", "Importar"].map((label, index) => {
        const active = step === index + 1;
        return <div key={label} className={`rounded-md border px-4 py-3 text-sm font-semibold ${active ? "border-blue-200 bg-blue-50 text-blue-700" : "border-slate-200 bg-white text-slate-500"}`}>{index + 1}. {label}</div>;
      })}
    </div>
  );
}

function SheetCard({ sheet, included, onIncluded }: { sheet: SheetAnalysis; included: boolean; onIncluded: (value: boolean) => void }) {
  const columns = Object.keys(sheet.sample_data[0] ?? {});
  return (
    <article className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-semibold text-slate-950">{sheet.sheet_name}</h3>
            <StructureBadge value={sheet.structure_label} />
          </div>
          <p className="mt-1 text-sm text-slate-500">{sheet.row_count} filas · {sheet.col_count} columnas</p>
        </div>
        <label className="inline-flex items-center gap-2 text-sm font-medium text-slate-700">
          <input type="checkbox" checked={included} onChange={(event) => onIncluded(event.target.checked)} />
          Incluir
        </label>
      </div>
      {sheet.structure_reasons.length > 0 ? (
        <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-amber-700">
          {sheet.structure_reasons.map((reason) => <li key={reason}>{reason}</li>)}
        </ul>
      ) : null}
      <PreviewPlainTable columns={columns} rows={sheet.sample_data.slice(0, 5)} />
    </article>
  );
}

function MappingTable({
  sheet,
  schema,
  sheetMapping,
  preview,
  headerRow,
  onHeaderRow,
  onChange
}: {
  sheet: SheetAnalysis;
  schema: SchemaResponse;
  sheetMapping: Record<string, string>;
  preview?: PreviewMappingResponse["sheets"][number];
  headerRow: number;
  onHeaderRow: (value: number) => void;
  onChange: (column: string, target: string) => void;
}) {
  return (
    <article className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-950">{sheet.sheet_name}</h3>
          <p className="text-sm text-slate-500">Advertencias: {preview?.warning_count ?? 0}</p>
        </div>
        <label className="text-sm font-medium text-slate-700">
          Header row
          <input className="ml-2 w-24" type="number" min={0} value={headerRow} onChange={(event) => onHeaderRow(Number(event.target.value))} />
        </label>
      </div>
      <div className="overflow-x-auto">
        <table className={tableClass}>
          <thead className="bg-slate-50">
            <tr><th className={thClass}>Columna Excel</th><th className={thClass}>Tipo detectado</th><th className={thClass}>Muestras</th><th className={thClass}>Campo destino</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sheet.columns_meta.map((column) => (
              <tr key={column.name}>
                <td className={tdClass}>{column.name}</td>
                <td className={tdClass}>{column.type}</td>
                <td className={tdClass}>{column.sample_values.map(formatValue).join(", ")}</td>
                <td className={tdClass}>
                  <select value={sheetMapping[column.name] ?? ignoreValue} onChange={(event) => onChange(column.name, event.target.value)}>
                    <option value={ignoreValue}>Ignorar</option>
                    {schema.fields.map((field) => <option key={field.name} value={field.name}>{field.label}</option>)}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {preview ? <PreviewWarningTable preview={preview} /> : <p className="mt-4 text-sm text-slate-500">Generando vista previa...</p>}
    </article>
  );
}

function PreviewWarningTable({ preview }: { preview: PreviewMappingResponse["sheets"][number] }) {
  const fields = preview.target_fields.map((field) => field.name);
  return (
    <div className="mt-5 overflow-x-auto">
      <table className={tableClass}>
        <thead className="bg-slate-50">
          <tr>{preview.target_fields.map((field) => <th key={field.name} className={thClass}>{field.label}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {preview.rows.map((row, index) => (
            <tr key={`${preview.sheet_name}-${index}`}>
              {fields.map((field) => {
                const warning = row.warnings[field];
                return <td key={field} title={warning} className={`${tdClass} ${warning ? "bg-amber-50 text-amber-900" : ""}`}>{formatValue(row.values[field])}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PreviewPlainTable({ columns, rows }: { columns: string[]; rows: Record<string, JsonValue>[] }) {
  if (columns.length === 0) return <p className="mt-4 text-sm text-slate-500">Sin muestra disponible.</p>;
  return (
    <div className="mt-4 overflow-x-auto">
      <table className={tableClass}>
        <thead className="bg-slate-50"><tr>{columns.map((column) => <th key={column} className={thClass}>{column}</th>)}</tr></thead>
        <tbody className="divide-y divide-slate-100">{rows.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column} className={tdClass}>{formatValue(row[column])}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function JobProgress({ job }: { job: JobResponse }) {
  const percent = job.rows_total > 0 ? Math.round((job.rows_processed / job.rows_total) * 100) : 0;
  return (
    <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between"><StatusBadge value={job.status} /><span className="text-sm text-slate-500">{job.rows_processed}/{job.rows_total}</span></div>
      <div className="h-3 overflow-hidden rounded-full bg-slate-100"><div className="h-full bg-blue-600" style={{ width: `${percent}%` }} /></div>
      <ul className="mt-4 max-h-48 space-y-1 overflow-auto text-sm text-slate-600">{job.logs.map((log) => <li key={`${log.t}-${log.msg}`}><span className="font-medium">{log.level}</span> {log.msg}</li>)}</ul>
      {job.status === "done" && job.result ? <p className="mt-4 text-sm text-green-700">Importadas {job.result.rows_imported} filas. <Link className="font-semibold underline" to="/explorer">Ir al explorador</Link></p> : null}
      {job.status === "failed" ? <p className="mt-4 text-sm text-red-700">{job.error ?? "La importación falló."}</p> : null}
    </div>
  );
}

function Summary({ label, value }: { label: string; value: number }) {
  return <div className="rounded-md border border-slate-200 p-4"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p></div>;
}

function mappingForIncluded(mapping: UploadMapping, sheets: SheetAnalysis[]): UploadMapping {
  return Object.fromEntries(sheets.map((sheet) => [sheet.sheet_name, mapping[sheet.sheet_name] ?? {}]));
}

function countMapped(mapping: UploadMapping) {
  return Object.values(mapping).reduce((sum, sheet) => sum + Object.values(sheet).filter((value) => value !== ignoreValue).length, 0);
}

function formatValue(value: JsonValue | undefined) {
  if (value === null || value === undefined) return "";
  return String(value);
}
