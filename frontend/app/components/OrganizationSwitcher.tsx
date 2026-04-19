"use client";

import { useMemo, useState } from "react";

type OrganizationOption = {
  id: string;
  name: string;
  vertical?: string | null;
  botCount?: number;
  channelCount?: number;
  pendingCount?: number;
};

export default function OrganizationSwitcher({
  organizations,
  selectedId,
  redirectTo,
  action,
  compact = false,
}: {
  organizations: OrganizationOption[];
  selectedId?: string | null;
  redirectTo: string;
  action: (formData: FormData) => void | Promise<void>;
  compact?: boolean;
}) {
  const [value, setValue] = useState(selectedId || "");
  const selected = useMemo(() => organizations.find((item) => item.id === value) || null, [organizations, value]);

  if (compact) {
    return (
      <form action={action} className="flex flex-wrap items-center gap-2">
        <input type="hidden" name="redirect_to" value={redirectTo} />
        <label className="sr-only" htmlFor="organization-scope-switcher">Organización</label>
        <select
          id="organization-scope-switcher"
          name="organization_id"
          value={value}
          onChange={(event) => setValue(event.currentTarget.value)}
          className="field-input min-w-[220px] py-2"
          aria-label="Cambiar organización actual"
        >
          <option value="">Seleccionar organización</option>
          {organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <button type="submit" className="secondary-btn" disabled={!value}>Cambiar organización</button>
      </form>
    );
  }

  return (
    <form action={action} className="space-y-4">
      <input type="hidden" name="redirect_to" value={redirectTo} />
      <label className="field-label">
        Organización
        <select
          name="organization_id"
          value={value}
          onChange={(event) => setValue(event.currentTarget.value)}
          className="field-input min-w-[240px] py-2"
          aria-label="Seleccionar organización"
        >
          <option value="">Selecciona una organización</option>
          {organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      </label>

      <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4 text-sm text-[color:var(--text-secondary)]">
        <div className="eyebrow">Vista previa del contexto</div>
        {selected ? (
          <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div className="surface-row">
              <div className="text-xs uppercase tracking-[0.16em] text-[color:var(--text-muted)]">Organización</div>
              <div className="mt-1 font-medium text-[color:var(--text-primary)]">{selected.name}</div>
            </div>
            <div className="surface-row">
              <div className="text-xs uppercase tracking-[0.16em] text-[color:var(--text-muted)]">Industria</div>
              <div className="mt-1 font-medium text-[color:var(--text-primary)]">{selected.vertical || "Se define al confirmar"}</div>
            </div>
            <div className="surface-row">
              <div className="text-xs uppercase tracking-[0.16em] text-[color:var(--text-muted)]">Asistentes operativos visibles</div>
              <div className="mt-1 font-medium text-[color:var(--text-primary)]">{typeof selected.botCount === "number" ? selected.botCount : "—"}</div>
            </div>
            <div className="surface-row">
              <div className="text-xs uppercase tracking-[0.16em] text-[color:var(--text-muted)]">Canales / pendientes</div>
              <div className="mt-1 font-medium text-[color:var(--text-primary)]">{typeof selected.channelCount === "number" ? selected.channelCount : "—"} · {typeof selected.pendingCount === "number" ? selected.pendingCount : "—"}</div>
            </div>
          </div>
        ) : (
          <div className="mt-3 text-sm text-[color:var(--text-muted)]">Selecciona una organización para ver el contexto que activará inbox, asistentes operativos, integraciones y releases.</div>
        )}
      </div>

      <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-4 text-sm text-[color:var(--text-secondary)]">
        <div className="font-medium text-[color:var(--text-primary)]">Qué cambia al confirmar</div>
        <p className="mt-2 leading-6">Fijas la organización activa para inbox, asistentes operativos, integraciones, agenda y publicaciones. Así evitas mezclar conversaciones o configuración entre clientes.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="submit" className="primary-btn" disabled={!value}>Confirmar contexto</button>
          <span className="text-xs leading-6 text-[color:var(--text-muted)]">Puedes cambiarlo después desde el header compartido.</span>
        </div>
      </div>
    </form>
  );
}
