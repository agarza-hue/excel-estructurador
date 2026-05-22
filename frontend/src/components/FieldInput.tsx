import type { ChangeEvent } from "react";
import type { RecordValue, SchemaField } from "../lib/types";

interface FieldInputProps {
  field: SchemaField;
  value: RecordValue;
  onChange: (value: RecordValue) => void;
}

export default function FieldInput({ field, value, onChange }: FieldInputProps) {
  const common = {
    id: field.name,
    required: field.required
  };

  if (field.type === "boolean") {
    return (
      <input
        {...common}
        type="checkbox"
        checked={Boolean(value)}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
      />
    );
  }

  if (field.type === "select") {
    return (
      <select {...common} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)}>
        <option value="">Selecciona...</option>
        {field.options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }

  const inputType = field.type === "date" ? "date" : field.type === "number" || field.type === "currency" ? "number" : "text";

  return (
    <input
      {...common}
      type={inputType}
      step={field.type === "currency" ? "0.01" : undefined}
      value={String(value ?? "")}
      onChange={(event: ChangeEvent<HTMLInputElement>) => onChange(event.target.value)}
    />
  );
}
