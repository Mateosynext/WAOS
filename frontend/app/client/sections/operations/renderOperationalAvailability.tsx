import { KeyValueList, TimelineList } from "@/app/components/primitives/data-display";
import { ClientSectionBlock } from "../../../components/client/ClientPortalPrimitives";
import { formatDateTime, formatNumber, safeText } from "../../../lib/ui";
import type { ClientOperationsPayload } from "./types";

export function renderOperationalAvailability({ availability }: { availability: ClientOperationsPayload["availability"] }) {
  return (
    <ClientSectionBlock title="Disponibilidad y citas de hoy" subtitle="Lectura rápida del impacto operativo visible para hoy.">
      <div className="space-y-3">
        <KeyValueList items={[
          { label: "Citas hoy", value: formatNumber(availability.summary.appointments || 0) },
          { label: "Bloqueos", value: formatNumber(availability.summary.blocked_ranges || 0) },
          { label: "Excepciones abiertas", value: formatNumber(availability.summary.open_exceptions || 0) },
        ]} />
        <TimelineList items={availability.appointments.slice(0, 6).map((item) => ({ title: `Cita ${safeText(item.id, "")}`, detail: `${safeText(item.status || "scheduled", "scheduled")} · ${formatDateTime(item.scheduled_for || "")}`, tone: "slate" as const }))} />
      </div>
    </ClientSectionBlock>
  );
}
