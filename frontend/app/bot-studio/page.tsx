import Link from "next/link";
import { applyBotVerticalAction, createBotAction } from "../actions";
import { EmptyActionState, ModuleCard, Section, Shell, StatCard, SuccessState } from "../components";
import { getCurrentBotId, getSession } from "../lib/session";
import { safeText, yesNo } from "../lib/ui";
import { getBotBehavior, getBotTemplates, getBots, getVerticalCatalog, getVerticalProfile } from "../lib/waos";

export default async function BotStudioPage() {
  const session = await getSession();
  const currentBotId = await getCurrentBotId();
  const currentOrg = session?.user.organizations.find((item) => item.id === session?.organizationId) || null;
  const [behavior, templates, verticals, bots] = await Promise.all([getBotBehavior(), getBotTemplates(), getVerticalCatalog(), getBots()]);
  const selectedBot = bots.find((item) => item.id === currentBotId) || null;
  const selectedVerticalId = selectedBot?.vertical || currentOrg?.vertical || verticals[0]?.id;
  const selectedVertical = selectedVerticalId ? await getVerticalProfile(selectedVerticalId) : null;

  if (!verticals.length) {
    return (
      <Shell
        title="Crear bot"
        subtitle="No se pudo cargar el catálogo de verticales desde el backend."
        action={<><Link href="/organizations" className="secondary-btn">Organizaciones</Link><Link href="/verticals" className="secondary-btn">Reintentar catálogo</Link></>}
      >
        <EmptyActionState
          title="Catálogo de verticales no disponible"
          description="La sesión está activa, pero la UI no recibió verticales. Revisa el endpoint /api/v1/verticals o vuelve a iniciar sesión."
          primaryAction={<Link href="/verticals" className="primary-btn">Abrir verticales</Link>}
        />
      </Shell>
    );
  }

  return (
    <Shell
      title="Crear bot"
      subtitle="Las 11 verticales madre ya viven en WAOS con presets de bot, comportamiento y plantillas listas para produccion. Ahora tambien puedes crear un bot nuevo o reaplicar vertical a uno existente desde esta pantalla."
      action={<><Link href="/bots" className="secondary-btn">Ver bots</Link><Link href="/flows" className="secondary-btn">Flujos</Link></>}
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Modo actual" value={safeText(behavior.bot_mode, "sin definir")} hint="Como esta operando hoy" icon="bot" tone="green" />
        <StatCard label="Tono" value={safeText(behavior.tone, "sin definir")} hint="Como responde al cliente" icon="spark" tone="blue" />
        <StatCard label="Imagenes automaticas" value={yesNo(behavior.auto_send_images)} hint="Si el bot manda imagenes solo" icon="image" tone="gold" />
        <StatCard label="Verticales listas" value={String(verticals.length)} hint="Catalogo madre disponible" icon="layers" tone="slate" />
      </div>

      <Section title="Crear bot nuevo con vertical" subtitle="Formulario real para crear un bot sobre la organizacion activa y sembrar templates, comportamiento y defaults productivos desde el primer minuto." icon="check">
        {currentOrg ? (
          <form action={createBotAction} className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <input type="hidden" name="organization_id" value={currentOrg.id} />
            <label className="field-label">Organizacion activa
              <input className="field-input" value={currentOrg.name} readOnly />
            </label>
            <label className="field-label">Vertical madre
              <select className="field-input" name="vertical" defaultValue={currentOrg.vertical || selectedVerticalId || ""} required>
                {verticals.map((vertical) => <option key={vertical.id} value={vertical.id}>{vertical.name}</option>)}
              </select>
            </label>
            <label className="field-label">Objetivo primario
              <select className="field-input" name="primary_objective" defaultValue="agendar">
                <option value="agendar">Agendar</option>
                <option value="vender">Vender</option>
                <option value="calificar">Calificar</option>
                <option value="responder">Responder</option>
                <option value="reactivar">Reactivar</option>
              </select>
            </label>
            <label className="field-label">Nombre del negocio
              <input className="field-input" name="business_name" placeholder="Ej. WAOS Dental Polanco" required />
            </label>
            <label className="field-label">Nombre del bot
              <input className="field-input" name="bot_name" placeholder="Ej. Sofia" required />
            </label>
            <label className="field-label">Tono base
              <input className="field-input" name="tone" defaultValue="amable" placeholder="amable" />
            </label>
            <label className="field-label">Idioma
              <select className="field-input" name="language" defaultValue="es">
                <option value="es">Español</option>
                <option value="en">English</option>
              </select>
            </label>
            <label className="field-label">Timezone
              <input className="field-input" name="timezone" defaultValue={currentOrg.timezone || "America/Mexico_City"} />
            </label>
            <label className="field-label">WhatsApp (opcional)
              <input className="field-input" name="whatsapp_number" placeholder="+525512345678" />
            </label>
            <label className="field-label md:col-span-2 xl:col-span-2">Horario inicial
              <input className="field-input" name="hours" placeholder="Lun-Vie 9:00-18:00" />
            </label>
            <label className="field-label flex items-center gap-3 self-end">
              <input type="checkbox" name="publish_now" defaultChecked />
              <span>Publicar primer draft al crear</span>
            </label>
            <div className="md:col-span-2 xl:col-span-3">
              <button className="primary-btn" type="submit">Crear bot con vertical</button>
            </div>
          </form>
        ) : (
          <EmptyActionState title="Primero selecciona una organizacion" description="Crear un bot sin tenant activo meteria ambiguedad en multi-tenant. Ve a organizaciones y fija contexto." primaryAction={<Link href="/organizations" className="primary-btn">Seleccionar organizacion</Link>} />
        )}
      </Section>

      <Section title="Aplicar vertical al bot seleccionado" subtitle="Si ya existe un bot, este formulario reaplica vertical, reescribe comportamiento y reemplaza templates para dejarlo alineado con la nueva operacion." icon="wand">
        {selectedBot ? (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
            <form action={applyBotVerticalAction} className="grid gap-4 md:grid-cols-2">
              <input type="hidden" name="bot_id" value={selectedBot.id} />
              <input type="hidden" name="redirect_to" value={`/bot-studio`} />
              <label className="field-label">Bot actual
                <input className="field-input" value={selectedBot.name} readOnly />
              </label>
              <label className="field-label">Vertical
                <select className="field-input" name="vertical" defaultValue={selectedBot.vertical || ""} required>
                  {verticals.map((vertical) => <option key={vertical.id} value={vertical.id}>{vertical.name}</option>)}
                </select>
              </label>
              <div className="md:col-span-2">
                <button className="primary-btn" type="submit">Aplicar vertical al bot</button>
              </div>
            </form>
            <SuccessState title={`Bot seleccionado: ${safeText(selectedBot.name)}`} description={`Vertical actual: ${safeText(selectedBot.vertical, "sin definir")}. Al aplicar una nueva vertical se resembran templates y comportamiento.`} actions={<Link href={`/bots/${selectedBot.id}`} className="secondary-btn">Ver detalle</Link>} />
          </div>
        ) : (
          <EmptyActionState title="No hay bot seleccionado" description="Selecciona uno en /bots para poder reaplicar vertical, o usa el formulario superior para crear uno nuevo." primaryAction={<Link href="/bots" className="primary-btn">Elegir bot</Link>} />
        )}
      </Section>

      <Section title="Preview de la vertical activa" subtitle="Esto es lo que WAOS ya entiende como problema, flujos e integraciones recomendadas para la vertical que hoy tienes enfrente." icon="layers">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ModuleCard title={safeText(selectedVertical?.name, "Vertical")} description={safeText(selectedVertical?.problem, "Vertical lista para operar.")} icon="wand" tone="green" footer={<span className="mono-pill">{safeText(selectedVertical?.short_name, "perfil")}</span>} />
          <ModuleCard title="Objetos operativos" description={selectedVertical?.objects.join(", ") || "Sin objetos definidos"} icon="catalog" tone="blue" />
          <ModuleCard title="Flujos clave" description={selectedVertical?.flows.join(" · ") || "Sin flujos definidos"} icon="route" tone="gold" />
          <ModuleCard title="Integraciones recomendadas" description={selectedVertical?.recommended_integrations.join(" · ") || "base operativa"} icon="plug" tone="slate" />
        </div>
      </Section>

      <Section title="Plantillas listas para empezar" subtitle="Cuando el bot ya existe, estas plantillas se siembran automaticamente segun la vertical elegida." icon="layers">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(templates || []).map((template) => (
            <ModuleCard
              key={template.id || template.name}
              title={template.name || "Plantilla"}
              description={template.description || template.detail || "Base de bot con tono, estructura y comportamiento sugerido."}
              icon="wand"
              tone="blue"
              footer={<span className="mono-pill">{template.vertical || "bot"}</span>}
            />
          ))}
          {!templates.length ? <ModuleCard title="Aun no hay templates visibles" description="En cuanto se cree un bot con vertical o se reaplique una vertical a un bot existente, veras las plantillas ya sembradas aqui." icon="check" tone="slate" /> : null}
        </div>
      </Section>
    </Shell>
  );
}
