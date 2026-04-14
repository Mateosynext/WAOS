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
