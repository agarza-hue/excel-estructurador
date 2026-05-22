import type { SourceBadge } from "../lib/types";

const statusMap: Record<string, string> = {
  done: "bg-green-100 text-green-800",
  running: "bg-blue-100 text-blue-800",
  pending: "bg-amber-100 text-amber-800",
  failed: "bg-red-100 text-red-800",
  created: "bg-green-100 text-green-800",
  reverted: "bg-slate-100 text-slate-700"
};

export function StatusBadge({ value }: { value: string }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${statusMap[value] ?? "bg-slate-100 text-slate-700"}`}>
      {value}
    </span>
  );
}

export function StructureBadge({ value }: { value: string }) {
  const cls = value.includes("limpia")
    ? "bg-green-100 text-green-800"
    : value.includes("cross")
      ? "bg-purple-100 text-purple-800"
      : value.includes("multi")
        ? "bg-amber-100 text-amber-800"
        : "bg-slate-100 text-slate-700";
  return <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${cls}`}>{value}</span>;
}

export function SourceBadgeView({ source, badge }: { source: string; badge?: SourceBadge }) {
  const normalized = badge ?? source;
  const cls =
    normalized === "verde" || source === "web_form"
      ? "bg-green-100 text-green-800"
      : normalized === "azul" || source === "api"
        ? "bg-blue-100 text-blue-800"
        : "bg-slate-100 text-slate-700";
  return <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${cls}`}>{source}</span>;
}
