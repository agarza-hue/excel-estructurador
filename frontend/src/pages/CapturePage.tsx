import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import FieldInput from "../components/FieldInput";
import { SourceBadgeView } from "../components/Badge";
import { ErrorBlock, LoadingBlock, PageHeader, buttonPrimary, buttonSecondary } from "../components/State";
import { ApiError, api } from "../lib/api";
import type { ApiValidationError, BusinessRecord, RecordValue, SchemaResponse } from "../lib/types";

export default function CapturePage() {
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [values, setValues] = useState<Record<string, RecordValue>>({});
  const [period, setPeriod] = useState("");
  const [recent, setRecent] = useState<BusinessRecord[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const requiredMissing = useMemo(
    () => schema?.fields.filter((field) => field.required && (values[field.name] === undefined || values[field.name] === "" || values[field.name] === null)) ?? [],
    [schema, values]
  );

  useEffect(() => {
    Promise.all([api.getSchema(), api.getRecentForm()])
      .then(([schemaResponse, recentResponse]) => {
        setSchema(schemaResponse);
        setRecent(recentResponse.items);
      })
      .catch(() => setError("No se pudo cargar el formulario de captura."));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!schema || requiredMissing.length > 0) return;
    setSaving(true);
    setWarnings([]);
    setError(null);
    try {
      await api.createRecord({ data: values, period: period || undefined });
      setValues({});
      const recentResponse = await api.getRecentForm();
      setRecent(recentResponse.items);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        const body = err.body as ApiValidationError;
        setWarnings(body.detail.warnings);
      } else {
        setError("No se pudo guardar el registro.");
      }
    } finally {
      setSaving(false);
    }
  }

  if (error && !schema) return <ErrorBlock message={error} />;
  if (!schema) return <LoadingBlock />;

  return (
    <>
      <PageHeader
        title="Registrar dato nuevo"
        subtitle="Captura manual validada contra el esquema de negocio."
        actions={
          <Link className={buttonSecondary} to="/upload">
            Importar desde CSV
          </Link>
        }
      />
      {error ? <div className="mb-4"><ErrorBlock message={error} /></div> : null}
      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <form onSubmit={onSubmit} className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-5">
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="period">
              Periodo
            </label>
            <input id="period" placeholder="Q1_2025" value={period} onChange={(event) => setPeriod(event.target.value)} />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {schema.fields.map((field) => {
              const missing = requiredMissing.some((item) => item.name === field.name);
              return (
                <label key={field.name} className="grid gap-1 text-sm font-medium text-slate-700">
                  <span>
                    {field.label}
                    {field.required ? <span className="text-red-600"> *</span> : null}
                  </span>
                  <FieldInput
                    field={field}
                    value={values[field.name]}
                    onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))}
                  />
                  {missing ? <span className="text-xs text-red-600">Campo requerido</span> : null}
                </label>
              );
            })}
          </div>
          {warnings.length > 0 ? (
            <div className="mt-5 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <p className="font-semibold">Validación fallida</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="mt-6">
            <button className={buttonPrimary} disabled={saving || requiredMissing.length > 0}>
              {saving ? "Guardando..." : "Guardar registro"}
            </button>
          </div>
        </form>

        <aside className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">Últimos 10 registros</h3>
          <div className="space-y-3">
            {recent.map((record) => (
              <div key={record._id} className="rounded-md border border-slate-200 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <SourceBadgeView source={record._source} badge={record._source_badge} />
                  <span className="text-xs text-slate-500">{record._period ?? "-"}</span>
                </div>
                <p className="truncate text-sm font-medium text-slate-800">{record._id}</p>
                <p className="mt-1 text-xs text-slate-500">{record._created_at}</p>
              </div>
            ))}
            {recent.length === 0 ? <p className="text-sm text-slate-500">Sin registros recientes.</p> : null}
          </div>
        </aside>
      </div>
    </>
  );
}
