import { notFound } from "next/navigation";
import { ClientPortalContent, type ClientSection } from "../ClientPortalContent";

const allowed = new Set<ClientSection>(["resumen", "conversaciones", "agenda", "promociones", "solicitudes", "bot"]);

export default async function ClientSectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!allowed.has(section as ClientSection)) notFound();
  return <ClientPortalContent section={section as ClientSection} />;
}
