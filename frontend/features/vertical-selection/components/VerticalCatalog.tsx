import Link from "next/link";
import { ContextTip } from "@/app/components/feedback";
import { Shell } from "@/app/components/layout/shell";
import { SegmentedLinks } from "@/app/components/navigation";
import { ModuleCard, Section } from "@/app/components/primitives/cards";
import { safeText } from "@/app/lib/ui";
import type { VerticalsPageModel } from "@/features/vertical-selection/server/getVerticalsPageModel";

export function VerticalCatalogEmpty({ model }: { model: VerticalsPageModel }) {
  const { verticals } = model;
  return (
    <Shell title="Portafolio vertical WAOS" subtitle="No se pudo cargar el catálogo de verticales." action={<Link href="/bot-studio" className="primary-btn">Ir a Bot Studio</Link>}>
      <Section title="Elige una vertical" subtitle="Esta vista ya no cae silenciosamente a la primera vertical del catálogo." icon="layers">
        {verticals.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {verticals.map((item) => <ModuleCard key={item.id} title={safeText(item.name)} description={safeText(item.description || item.problem, "Sin descripción visible.")} icon="layers" tone="green" footer={<Link href={`/verticals?vertical=${encodeURIComponent(item.id)}`} className="secondary-btn">Abrir vertical</Link>} />)}
          </div>
        ) : (
          <ModuleCard title="Sin verticales disponibles" description="Recarga la página, vuelve a iniciar sesión o revisa la conexión del frontend con /api/v1/verticals." icon="alert" tone="red" />
        )}
      </Section>
    </Shell>
  );
}

export function VerticalCatalog({ model }: { model: VerticalsPageModel }) {
  const { segmented, strongestVerticals, profile } = model;
  if (!profile) return null;
  return (
    <>
      <Section title="Vertical activa" subtitle="Selecciona una línea de producto para ver su tesis comercial y operativa." icon="layers">
        <SegmentedLinks items={segmented} />
      </Section>
      <ContextTip title="Qué cambia con esta capa">
        WAOS ya no se presenta como un bot que responde, sino como una torre de control comercial y operativa sobre WhatsApp: inbox, takeover humano, memoria, follow-ups, agenda, pagos, catálogo, promociones, revenue, operaciones, insights, launch y despliegue.
      </ContextTip>
      <Section title="Las 5 verticales más fuertes" subtitle="Prioridad 10x para vender, activar y operar WAOS con más profundidad por vertical y subvertical." icon="rocket">
        <div className="grid gap-4 xl:grid-cols-5">
          {strongestVerticals.map((item) => (
            <ModuleCard key={item.id} title={`${item.strongest_rank || "-"}. ${safeText(item.name).replace(/^WAOS\s+/i, "")}`} description={safeText(item.ten_x_narrative, item.description)} icon="target" tone={item.id === profile.id ? "green" : "slate"} footer={<div className="text-xs text-slate-400">Score {safeText(item.ten_x_score)} • Subverticales foco: {safeText(item.recommended_subverticals.join(" • "), "Sin foco")}</div>} />
          ))}
        </div>
      </Section>
    </>
  );
}
