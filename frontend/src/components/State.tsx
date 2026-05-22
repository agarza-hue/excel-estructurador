import type { ReactNode } from "react";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h2 className="text-2xl font-semibold text-slate-950">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}

export function LoadingBlock({ label = "Cargando..." }: { label?: string }) {
  return <div className="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">{label}</div>;
}

export function ErrorBlock({ message }: { message: string }) {
  return <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{message}</div>;
}

export const buttonPrimary =
  "inline-flex items-center justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60";

export const buttonSecondary =
  "inline-flex items-center justify-center rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60";

export const tableClass = "min-w-full divide-y divide-slate-200 text-sm";
export const thClass = "whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500";
export const tdClass = "whitespace-nowrap px-3 py-3 text-slate-700";
