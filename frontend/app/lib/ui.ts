export function formatNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  if (Number.isNaN(number)) return String(value);
  return new Intl.NumberFormat("es-MX").format(number);
}

export function formatMoney(value: number | string | null | undefined, currency = "MXN") {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  if (Number.isNaN(number)) return String(value);
  return new Intl.NumberFormat("es-MX", { style: "currency", currency }).format(number);
}

export function yesNo(value: unknown) {
  return Number(value) === 1 || value === true ? "Sí" : "No";
}

export function safeText(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

export function listOrFallback(values: unknown[] | null | undefined, fallback = "Sin datos") {
  if (!values || !values.length) return fallback;
  return values.map((item) => String(item)).join(", ");
}

export function humanizeToken(value: unknown, fallback = "Sin dato") {
  const raw = safeText(value, fallback);
  if (raw === fallback) return fallback;
  return raw
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

export function formatDateTime(value: string | null | undefined, locale = "es-MX") {
  if (!value) return "Sin fecha";
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

export function formatDate(value: string | null | undefined, locale = "es-MX") {
  if (!value) return "Sin fecha";
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(parsed);
}

export function summarizeCount(label: string, count: number) {
  if (!count) return `Sin ${label.toLowerCase()} visibles`;
  if (count === 1) return `1 ${label.toLowerCase().replace(/s$/, "")} visible`;
  return `${formatNumber(count)} ${label.toLowerCase()} visibles`;
}
