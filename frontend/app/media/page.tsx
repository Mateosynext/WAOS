import { DataTable, Section, Shell, StatCard } from "../components";
import { formatNumber, safeText } from "../lib/ui";
import { getMediaAssets } from "../lib/waos";

export default async function MediaPage() {
  const assets = await getMediaAssets();
  return (
    <Shell title="Archivos" subtitle="Aquí concentras imágenes, documentos y material que el bot usa para responder o vender mejor.">
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Archivos" value={formatNumber(assets.length)} hint="Total cargado" icon="image" tone="blue" />
        <StatCard label="Imágenes" value={formatNumber(assets.filter((item) => String(item.asset_type || item.type || "").includes("image")).length)} hint="Visuales disponibles" icon="image" tone="green" />
        <StatCard label="Documentos" value={formatNumber(assets.filter((item) => { const assetType = String(item.asset_type || item.type || ""); return assetType.includes("pdf") || assetType.includes("doc"); }).length)} hint="Soporte o fichas" icon="folder" tone="gold" />
      </div>
      <Section title="Biblioteca" subtitle="Una vista clara del material que ya está listo para usarse en el bot." icon="folder">
        <DataTable columns={["Nombre", "Tipo", "Etiqueta", "URL"]} rows={assets.map((item) => [safeText(item.name || item.file_name), safeText(item.asset_type || item.type), safeText(item.label), safeText(item.file_url || item.url)])} />
      </Section>
    </Shell>
  );
}
