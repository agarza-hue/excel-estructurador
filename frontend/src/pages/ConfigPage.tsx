import { useEffect, useState } from "react";
import { StatusBadge } from "../components/Badge";
import { ErrorBlock, LoadingBlock, PageHeader, buttonPrimary, buttonSecondary, tableClass, tdClass, thClass } from "../components/State";
import { api } from "../lib/api";
import type { FieldType, Ingestion, SchemaField, SchemaResponse } from "../lib/types";

const fieldTypes: FieldType[] = ["text", "number", "currency", "date", "boolean", "select"];

export default function ConfigPage() {
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [ingestions, setIngestions] = useState<Ingestion[]>([]);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    refresh().catch(() => setError("No se pudo cargar la configuración."));
  }, []);

  async function refresh() {
    const [schemaResponse, ingestionsResponse] = await Promise.all([api.getSchema(), api.getIngestions()]);
    setSchema(schemaResponse);
    setIngestions(ingestionsResponse.items);
  }

  function updateField(index: number, patch: Partial<SchemaField>) {
    if (!schema) return;
    setSchema({ ...schema, fields: schema.fields.map((field, i) => i === index ? { ...field, ...patch } : field) });
  }

  function removeField(index: number) {
    if (!schema) return;
    setSchema({ ...schema, fields: schema.fields.filter((_, i) => i !== index) });
  }

  function addField() {
    if (!schema) return;
    setSchema({ ...schema, fields: [...schema.fields, { name: "", label: "", type: "text", required: false, options: [] }] });
  }

  async function save() {
    if (!schema) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await api.updateSchema(schema);
      setSchema(saved);
    } catch {
      setError("No se pudo guardar el esquema.");
    } finally {
      setSaving(false);
    }
  }

  async function revert(ingestion: Ingestion) {
    if (!window.confirm(`Revertir la ingesta ${ingestion.filename}?`)) return;
    try {
      await api.revertIngestion(ingestion.id);
      const response = await api.getIngestions();
      setIngestions(response.items);
    } catch {
      setError("No se pudo revertir la ingesta.");
    }
  }

  if (error && !schema) return <ErrorBlock message={error} />;
  if (!schema) return <LoadingBlock />;

  return (
    <>
      <PageHeader title="Configuración" subtitle={`Esquema versión ${schema.version}`} actions={<button className={buttonPrimary} onClick={save} disabled={saving}>{saving ? "Guardando..." : "Guardar"}</button>} />
      {error ? <div className="mb-4"><ErrorBlock message={error} /></div> : null}
      <section className="mb-6 rounded-md border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-950">Editor de esquema</h3>
          <button className={buttonSecondary} onClick={addField}>Agregar campo</button>
        </div>
        <div className="overflow-x-auto">
          <table className={tableClass}>
            <thead className="bg-slate-50"><tr><th className={thClass}>Nombre</th><th className={thClass}>Etiqueta</th><th className={thClass}>Tipo</th><th className={thClass}>Requerido</th><th className={thClass}>Opciones</th><th className={thClass}></th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {schema.fields.map((field, index) => (
                <tr key={`${field.name}-${index}`}>
                  <td className={tdClass}><input value={field.name} onChange={(event) => updateField(index, { name: event.target.value })} /></td>
                  <td className={tdClass}><input value={field.label} onChange={(event) => updateField(index, { label: event.target.value })} /></td>
                  <td className={tdClass}><select value={field.type} onChange={(event) => updateField(index, { type: event.target.value as FieldType })}>{fieldTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></td>
                  <td className={tdClass}><input type="checkbox" checked={field.required} onChange={(event) => updateField(index, { required: event.target.checked })} /></td>
                  <td className={tdClass}><input value={field.options.join(", ")} onChange={(event) => updateField(index, { options: parseOptions(event.target.value) })} disabled={field.type !== "select"} /></td>
                  <td className={tdClass}><button className={buttonSecondary} onClick={() => removeField(index)}>Quitar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-md border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4"><h3 className="text-lg font-semibold text-slate-950">Ingestas</h3></div>
        <div className="overflow-x-auto">
          <table className={tableClass}>
            <thead className="bg-slate-50"><tr><th className={thClass}>Archivo</th><th className={thClass}>Periodo</th><th className={thClass}>Estado</th><th className={thClass}>Filas</th><th className={thClass}>Warnings</th><th className={thClass}></th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {ingestions.map((ingestion) => (
                <tr key={ingestion.id}>
                  <td className={tdClass}>{ingestion.filename}</td>
                  <td className={tdClass}>{ingestion.period ?? "-"}</td>
                  <td className={tdClass}><StatusBadge value={ingestion.reverted ? "reverted" : ingestion.status} /></td>
                  <td className={tdClass}>{ingestion.rows_imported}/{ingestion.rows_total}</td>
                  <td className={tdClass}><button className="text-blue-700 underline disabled:text-slate-400" disabled={ingestion.warnings.length === 0} onClick={() => setExpanded((current) => ({ ...current, [ingestion.id]: !current[ingestion.id] }))}>{ingestion.warnings.length}</button>{expanded[ingestion.id] ? <ul className="mt-2 list-disc pl-5 text-amber-700">{ingestion.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}</td>
                  <td className={tdClass}>{!ingestion.reverted ? <button className={buttonSecondary} onClick={() => revert(ingestion)}>Revertir</button> : null}</td>
                </tr>
              ))}
              {ingestions.length === 0 ? <tr><td className={tdClass} colSpan={6}>Sin ingestas.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function parseOptions(value: string) {
  return value.split(",").map((option) => option.trim()).filter(Boolean);
}
