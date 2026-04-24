import Link from "next/link";
import { Shell } from "@/app/components/layout/shell";
import { getSession } from "../lib/session";
import type { PortalModuleState } from "@/app/lib/data/shared";
import { getClientPortalData } from "../lib/data/client-portal";
import { buildClientPortalTimeline, clientSectionMeta, type ClientSection } from "./clientPortalViewModel";
import { renderAgenda, renderBot, renderConversations, renderModuleErrors, renderOperations, renderPromotions, renderRequests, renderSummary } from "./ClientPortalSections";

export type { ClientSection } from "./clientPortalViewModel";

export async function ClientPortalContent({ section }: { section: ClientSection }) {
  const session = await getSession();
  const currentOrg = session?.user.organizations?.find((item) => item.id === session?.organizationId) || null;
  const data = await getClientPortalData(section, currentOrg?.vertical);
  const timeline = buildClientPortalTimeline(data);
  const meta = clientSectionMeta[section];

  const modulesForErrors: Array<{ label: string; state: PortalModuleState<unknown> }> = [
    { label: "Conversaciones", state: data.conversations },
    { label: "Agenda", state: data.appointments },
    { label: "Resumen de agenda", state: data.agendaOverview },
    { label: "Solicitudes", state: data.requests },
    { label: "Feedback", state: data.feedback },
    { label: "Promociones", state: data.promotions },
    { label: "Bot", state: data.behavior },
    { label: "Perfil vertical", state: data.verticalProfile },
  ];

  return (
    <Shell
      mode="client"
      title={meta.title}
      subtitle={meta.subtitle}
      action={<Link href={meta.actionHref} className="primary-btn">{meta.actionLabel}</Link>}
    >
      <div className="space-y-6">
        {renderModuleErrors(modulesForErrors)}
        {section === "resumen" ? renderSummary(data, timeline) : null}
        {section === "conversaciones" ? renderConversations(data) : null}
        {section === "agenda" ? renderAgenda(data) : null}
        {section === "solicitudes" ? renderRequests(data, timeline) : null}
        {section === "promociones" ? renderPromotions(data) : null}
        {section === "bot" ? renderBot(data) : null}
        {section === "operaciones" ? await renderOperations(data) : null}
      </div>
    </Shell>
  );
}
