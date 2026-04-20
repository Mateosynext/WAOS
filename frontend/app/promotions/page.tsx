import { redirect } from "next/navigation";

type SearchParams = Record<string, string | string[] | undefined>;
function appendSearchParams(tab: string, searchParams?: SearchParams) { const params = new URLSearchParams(); params.set("tab", tab); Object.entries(searchParams || {}).forEach(([key, value]) => { if (key === "tab") return; if (Array.isArray(value)) value.forEach((item) => params.append(key, item)); else if (value) params.set(key, value); }); return `/business-hub?${params.toString()}`; }
export default async function PromotionsRedirectPage({ searchParams }: { searchParams?: Promise<SearchParams> }) { redirect(appendSearchParams("promociones", (await searchParams) || {})); }
