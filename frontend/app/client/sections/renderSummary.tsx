import Link from "next/link";

import { ModuleCard } from "@/app/components/primitives/cards";
import { KeyValueList, StoryBeat } from "@/app/components/primitives/data-display";
import {
  ClientConversationCard,
  ClientEmptyBlock,
  ClientExecutiveSummary,
  ClientMetricCard,
  ClientSectionBlock,
} from "../../components/client/ClientPortalPrimitives";
import type { ClientPortalData } from "@/app/lib/data/client-portal";
import { buildClientPortalSummaryViewModel, type ClientTimelineEntry } from "../clientPortalViewModel";

export function renderSummary(data: ClientPortalData, timeline: ClientTimelineEntry[]) {
  const summary = buildClientPortalSummaryViewModel(data, timeline);

  return (
    <div className="space-y-6">
      <ClientExecutiveSummary
        title="Una portada pensada para entender qué pasó, qué sigue y qué puedes decidir en menos de un minuto"
        description="El portal cliente ya no depende de tablas frías ni de componentes genéricos. Esta vista prioriza progreso visible, actividad reciente, próximos pasos y señales del negocio para que cualquier persona no técnica pueda orientarse rápido."
        insights={summary.executiveHighlights}
        cta={
          <>
            <Link href="/client/solicitudes" className="primary-btn">Revisar pendientes</Link>
            <Link href="/client/conversaciones" className="secondary-btn">Abrir conversaciones</Link>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <ClientMetricCard label="Conversaciones" value={summary.metrics.conversations.value} description={summary.metrics.conversations.description} icon="chat" tone="blue" />
        <ClientMetricCard label="Agenda" value={summary.metrics.agenda.value} description={summary.metrics.agenda.description} icon="calendar" tone="green" />
        <ClientMetricCard label="Pendientes" value={summary.metrics.pending.value} description={summary.metrics.pending.description} icon="folder" tone="gold" />
        <ClientMetricCard label="Promociones" value={summary.metrics.promotions.value} description={summary.metrics.promotions.description} icon="promo" tone="slate" />
      </div>

      <ClientSectionBlock title="Panorama actual" subtitle="Tres bloques para leer el estado del portal sin ruido técnico.">
        <div className="grid gap-4 xl:grid-cols-3">
          <StoryBeat step="Qué pasó" title="Actividad reciente" description={summary.storyBeats.activity.description} outcome={summary.storyBeats.activity.outcome} tone="blue" />
          <StoryBeat step="Qué sigue" title="Agenda y seguimiento" description={summary.storyBeats.agenda.description} outcome={summary.storyBeats.agenda.outcome} tone="green" />
          <StoryBeat step="Qué decidir" title="Solicitudes y feedback" description={summary.storyBeats.decisions.description} outcome={summary.storyBeats.decisions.outcome} tone="gold" />
        </div>
      </ClientSectionBlock>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <ClientSectionBlock title="Actividad reciente" subtitle="La mezcla justa entre conversaciones y seguimiento, presentada de forma humana.">
          <div className="grid gap-4 lg:grid-cols-2">
            {summary.topConversations.map((item) => (
              <ClientConversationCard key={item.id} title={item.title} summary={item.summary} status={item.status} meta={item.meta} preview={item.preview} />
            ))}
            {!summary.topConversations.length ? <ClientEmptyBlock title="Aún no hay conversaciones visibles" description="Cuando exista actividad real, este bloque mostrará el resumen y el estado sin exponer bandejas internas." /> : null}
          </div>
        </ClientSectionBlock>

        <ClientSectionBlock title="Contexto del negocio" subtitle="Lo que WAOS ya entendió de la operación activa para darle sentido al portal.">
          <div className="grid gap-4">
            <ModuleCard title={summary.businessContext.verticalTitle} description={summary.businessContext.verticalProblem} tone="green" icon="layers" />
            <KeyValueList
              items={[
                { label: "Subvertical activa", value: summary.businessContext.selectedSubvertical },
                { label: "Pack aplicado", value: summary.businessContext.packCoverage },
                { label: "Objetos operativos", value: summary.businessContext.objectsCount },
                { label: "Flujos esperados", value: summary.businessContext.flowsCount },
                { label: "KPI sugeridos", value: summary.businessContext.kpiCount },
              ]}
            />
            <ModuleCard
              title="Promesa activa"
              description={summary.businessContext.promise}
              tone="blue"
              icon="spark"
              footer={<div className="text-xs text-slate-400">Foco portal: {summary.businessContext.focus}</div>}
            />
          </div>
        </ClientSectionBlock>
      </div>
    </div>
  );
}
