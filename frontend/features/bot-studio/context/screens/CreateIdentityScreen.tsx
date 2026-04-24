"use client";

import { FieldGroup, InputField, SelectField, TextAreaField } from "@/features/bot-studio/ui/flowUi";
import type { CreateIdentityActions, CreateIdentityViewModel } from "../createScreenTypes";

export function CreateIdentityScreen({ viewModel: state, actions: handlers }: { viewModel: CreateIdentityViewModel; actions: CreateIdentityActions }) {
  return (
    <FieldGroup testId="create-identity-step" title="Define la identidad operativa" description="Aquí decides cómo se presenta el bot. No mezclamos catálogo ni reglas todavía.">
      <div className="grid gap-4 lg:grid-cols-2">
        <InputField testId="business-name-input" label="Nombre del negocio" value={state.businessName} onChange={handlers.setBusinessName} />
        <InputField testId="bot-name-input" label="Nombre del bot" value={state.botName} onChange={handlers.setBotName} />
        <InputField testId="tone-input" label="Tono" value={state.tone} onChange={handlers.setTone} />
        <SelectField
          testId="language-select"
          label="Idioma"
          value={state.language}
          onChange={handlers.setLanguage}
          options={[{ label: "Español", value: "es" }, { label: "English", value: "en" }]}
        />
        <InputField testId="timezone-input" label="Zona horaria" value={state.timezone} onChange={handlers.setTimezone} />
        <InputField testId="whatsapp-number-input" label="WhatsApp visible" value={state.whatsappNumber} onChange={handlers.setWhatsappNumber} />
      </div>
      <TextAreaField testId="hours-textarea" label="Horario operativo" value={state.hours} onChange={handlers.setHours} rows={4} />
    </FieldGroup>
  );
}
