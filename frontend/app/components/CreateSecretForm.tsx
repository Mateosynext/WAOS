"use client";
import { useMemo, useState } from "react";
import { validateSecret } from "../lib/forms";
import { FieldError, UiMessage } from "./UiMessage";
export default function CreateSecretForm({ action, organizationId, bots }: { action: (formData: FormData) => void | Promise<void>; organizationId: string; bots: Array<{ id: string; name: string }> }) {
  const [scope, setScope] = useState("tenant");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const requiresBot = useMemo(() => scope === "bot", [scope]);
  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    const values = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>;
    const nextErrors = validateSecret(values); setErrors(nextErrors); const firstError = Object.values(nextErrors)[0] || null; setSummaryError(firstError); if (Object.keys(nextErrors).length) event.preventDefault();
  }
  return <form action={action} className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" onSubmit={onSubmit} noValidate><input type="hidden" name="organization_id" value={organizationId || ""} /><input type="hidden" name="redirect_to" value="/secrets" />{summaryError ? <div className="md:col-span-2 xl:col-span-4"><UiMessage title="Revisa el formulario" tone="error">{summaryError}</UiMessage></div> : null}<label className="field-label">Nombre<input className="field-input" name="key_name" placeholder="render-api-key" required /><FieldError message={errors.key_name} /></label><label className="field-label">Valor<input className="field-input" name="secret_value" placeholder="••••••••" required /><FieldError message={errors.secret_value} /></label><label className="field-label">Alcance<select className="field-input" name="scope" defaultValue="tenant" onChange={(event) => setScope(event.target.value)}><option value="tenant">Organización</option><option value="bot">Bot</option></select><FieldError message={errors.scope} /></label><label className="field-label">Bot (opcional)<select className="field-input" name="bot_id" defaultValue="" disabled={!requiresBot}><option value="">{requiresBot ? "Selecciona un bot" : "Sin bot específico"}</option>{bots.map((bot) => <option key={bot.id} value={bot.id}>{bot.name}</option>)}</select><FieldError message={errors.bot_id} /></label><button className="primary-btn md:col-span-2 xl:col-span-4" type="submit">Crear</button></form>;
}
