import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { StatusBadge } from "../components/Badge";
import { ErrorBlock, LoadingBlock, PageHeader, buttonPrimary, buttonSecondary, tableClass, tdClass, thClass } from "../components/State";
import { api } from "../lib/api";
import type { DashboardStats } from "../lib/types";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getStats()
      .then(setStats)
      .catch(() => setError("No se pudieron cargar las estadísticas."));
  }, []);

  if (error) return <ErrorBlock message={error} />;
  if (!stats) return <LoadingBlock />;

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Resumen operativo de históricos, capturas nuevas e ingestas recientes."
        actions={
          <>
            <Link className={buttonPrimary} to="/upload">
              Subir Excel histórico
            </Link>
            <Link className={buttonSecondary} to="/capture">
              Registrar dato nuevo
            </Link>
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-3">
        <CounterCard label="Históricos" value={stats.historico} />
        <CounterCard label="Nuevos" value={stats.nuevos} />
        <CounterCard label="Total" value={stats.total} />
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1fr_1.2fr]">
        <div className="rounded-md border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">Registros por periodo</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.by_period}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="n" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-4 py-3">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Últimas ingestas</h3>
          </div>
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead className="bg-slate-50">
                <tr>
                  <th className={thClass}>Fecha</th>
                  <th className={thClass}>Archivo</th>
                  <th className={thClass}>Periodo</th>
                  <th className={thClass}>Estado</th>
                  <th className={thClass}>Filas</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {stats.recent_ingestions.map((ingestion) => (
                  <tr key={ingestion.id}>
                    <td className={tdClass}>{formatDate(ingestion.created_at)}</td>
                    <td className={tdClass}>{ingestion.filename}</td>
                    <td className={tdClass}>{ingestion.period ?? "-"}</td>
                    <td className={tdClass}>
                      <StatusBadge value={ingestion.reverted ? "reverted" : ingestion.status} />
                    </td>
                    <td className={tdClass}>{ingestion.rows_imported}</td>
                  </tr>
                ))}
                {stats.recent_ingestions.length === 0 ? (
                  <tr>
                    <td className={tdClass} colSpan={5}>
                      Sin ingestas registradas.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </>
  );
}

function CounterCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-3 text-4xl font-semibold text-slate-950">{value.toLocaleString("es-MX")}</p>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
