import Link from "next/link";

import { ClientNotice } from "../../components/client/ClientPortalPrimitives";
import type { PortalModuleState } from "../../lib/waos";
import { loadedModuleNotices } from "../clientPortalViewModel";

export function renderModuleErrors(modules: Array<{ label: string; state: PortalModuleState<unknown> }>) {
  const errors = loadedModuleNotices(modules);
  if (!errors.length) return null;
  return (
    <div className="space-y-3">
      {errors.map(({ label, state }) => (
        <ClientNotice
          key={label}
          title={`No pudimos refrescar ${label.toLowerCase()}`}
          description={state.error?.message || "La sección usó el último fallback disponible para no dejar la vista en blanco."}
          tone="warning"
          detail={`Endpoint verificado: ${state.endpoint}`}
          action={<Link href="/client/resumen" className="secondary-btn">Actualizar vista</Link>}
        />
      ))}
    </div>
  );
}
