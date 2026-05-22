import { FormEvent, useEffect, useMemo, useState } from "react";
import { SourceBadgeView } from "../components/Badge";
import { ErrorBlock, LoadingBlock, PageHeader, buttonPrimary, buttonSecondary, tableClass, tdClass, thClass } from "../components/State";
import { api } from "../lib/api";
import type { BusinessRecord, RecordsQuery, RecordsResponse } from "../lib/types";

const pageSize = 25;
const metadataFields = new Set(["_id", "_source", "_source_badge", "_period", "_created_at"]);

export default function ExplorerPage() {
  const [filters, setFilters] = useState<RecordsQuery>({ limit: pageSize, offset: 0 });
  const [data, setData] = useState<RecordsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getRecords(filters).then(setData).catch(() => setError("No se pudieron cargar los registros.")).finally(() => setLoading(false));
  }, [filters]);

  const columns = useMemo(() => buildColumns(data?.items ?? []), [data]);
  const canPrev = (filters.offset ?? 0) > 0;
  const canNext = data ? (filters.offset ?? 0) + pageSize < data.total : false;

  function submit(event: FormEvent) {
    event.preventDefault();
    setFilters((current) => ({ ...current, offset: 0 }));
  }

  function update(name: keyof RecordsQuery, value: string) {
    setFilters((current) => ({ ...current, [name]: value || undefined, offset: 0 }));
  }

  function exportRecords(format: "csv" | "xlsx") {
    window.open(api.exportRecordsUrl(format, filters), "_blank", "noopener,noreferrer");
  }

  if (error && !data) return <ErrorBlock message={error} />;

  return (
    <>
      <PageHeader title="Explorador" subtitle="Consulta, filtra y exporta los registros consolidados." actions={<><button className={buttonSecondary} onClick={() => exportRecords("csv")}>Exportar CSV</button><button className={buttonPrimary} onClick={() => exportRecords("xlsx")}>Exportar Excel</button></>} />
      <form onSubmit={submit} className="mb-5 grid gap-3 rounded-md border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-3 xl:grid-cols-6">
        <input placeholder="Periodo" value={filters.period ?? ""} onChange={(event) => update("period", event.target.value)} />
        <select value={filters.source ?? ""} onChange={(event) => update("source", event.target.value)}>
          <option value="">Todas las fuentes</option>
          <option value="excel_historico">excel_historico</option>
          <option value="web_form">web_form</option>
          <option value="api">api</option>
        </select>
        <input type="date" value={filters.from_date ?? ""} onChange={(event) => update("from_date", event.target.value)} />
        <input type="date" value={filters.to_date ?? ""} onChange={(event) => update("to_date", event.target.value)} />
        <input placeholder="Buscar" value={filters.search ?? ""} onChange={(event) => update("search", event.target.value)} />
        <button className={buttonSecondary}>Filtrar</button>
      </form>
      {loading && !data ? <LoadingBlock /> : null}
      {data ? (
        <section className="rounded-md border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-2 border-b border-slate-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm font-semibold text-slate-800">Total: {data.total.toLocaleString("es-MX")}</p>
            <p className="text-sm text-slate-500">{Object.entries(data.breakdown_by_source).map(([source, count]) => `${source}: ${count}`).join(" · ") || "Sin desglose"}</p>
          </div>
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead className="bg-slate-50"><tr><th className={thClass}>Fuente</th><th className={thClass}>Periodo</th><th className={thClass}>Creado</th>{columns.map((column) => <th key={column} className={thClass}>{column}</th>)}</tr></thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((record) => <RecordRow key={record._id} record={record} columns={columns} />)}
                {data.items.length === 0 ? <tr><td className={tdClass} colSpan={columns.length + 3}>Sin resultados.</td></tr> : null}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3">
            <button className={buttonSecondary} disabled={!canPrev} onClick={() => setFilters((current) => ({ ...current, offset: Math.max(0, (current.offset ?? 0) - pageSize) }))}>Anterior</button>
            <span className="text-sm text-slate-500">{(filters.offset ?? 0) + 1}-{Math.min((filters.offset ?? 0) + pageSize, data.total)}</span>
            <button className={buttonSecondary} disabled={!canNext} onClick={() => setFilters((current) => ({ ...current, offset: (current.offset ?? 0) + pageSize }))}>Siguiente</button>
          </div>
        </section>
      ) : null}
    </>
  );
}

function RecordRow({ record, columns }: { record: BusinessRecord; columns: string[] }) {
  return (
    <tr>
      <td className={tdClass}><SourceBadgeView source={record._source} badge={record._source_badge} /></td>
      <td className={tdClass}>{record._period ?? "-"}</td>
      <td className={tdClass}>{formatCell(record._created_at)}</td>
      {columns.map((column) => <td key={column} className={tdClass}>{formatCell(record[column])}</td>)}
    </tr>
  );
}

function buildColumns(items: BusinessRecord[]) {
  const columns = new Set<string>();
  items.forEach((item) => Object.keys(item).forEach((key) => { if (!metadataFields.has(key)) columns.add(key); }));
  return Array.from(columns);
}

function formatCell(value: BusinessRecord[string]) {
  if (value === undefined || value === null) return "";
  return String(value);
}
