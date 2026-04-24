export function unique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((item) => String(item || "").trim()).filter(Boolean)));
}

export type DiffStatus = "replace" | "keep" | "suggest" | "add" | "remove";

export function diffStatusMeta(status: DiffStatus | string | undefined) {
  switch (status) {
    case "replace":
      return { pill: "se reemplaza", tone: "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] text-[color:var(--warning-text)]" };
    case "keep":
      return { pill: "se conserva", tone: "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success-text)]" };
    case "add":
      return { pill: "se agrega", tone: "border-[color:var(--accent-border)] bg-[color:var(--accent-soft)] text-[color:var(--text-primary)]" };
    case "remove":
      return { pill: "se elimina", tone: "border-[color:var(--danger-border)] bg-[color:var(--danger-soft)] text-[color:var(--danger-text)]" };
    default:
      return { pill: "se sugiere", tone: "border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] text-[color:var(--text-secondary)]" };
  }
}

export function validationStatusMeta(status: "green" | "yellow" | "red" | string | undefined) {
  switch (status) {
    case "green":
      return { pill: "verde", tone: "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success-text)]" };
    case "yellow":
      return { pill: "amarillo", tone: "border-[color:var(--warning-border)] bg-[color:var(--warning-soft)] text-[color:var(--warning-text)]" };
    default:
      return { pill: "rojo", tone: "border-[color:var(--danger-border)] bg-[color:var(--danger-soft)] text-[color:var(--danger-text)]" };
  }
}

export function SummaryList({ items, fallback }: { items: string[]; fallback: string }) {
  const visible = unique(items).slice(0, 5);
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {visible.length
        ? visible.map((item) => <span key={item} className="mono-pill">{item}</span>)
        : <span className="text-sm leading-6 text-[color:var(--text-secondary)]">{fallback}</span>}
    </div>
  );
}
