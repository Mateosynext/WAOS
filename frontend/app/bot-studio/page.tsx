import Link from "next/link";
import { applyBotVerticalAction, createBotAction, createBotDraftSnapshotAction, createBotSimulationCaseAction, runBotSimulationAction } from "../actions";
import { ContextTip, EmptyActionState, ModuleCard, Section, Shell, StatCard, SuccessState } from "../components";
import { getCurrentBotId, getSession } from "../lib/session";
import { safeText, yesNo } from "../lib/ui";
import { getBotBehavior, getBotSimulationCases, getBotSimulationRuns, getBotTemplates, getBots, getVerticalCatalog, getVerticalProfile } from "../lib/waos";

export default async function BotStudioPage() {
  const session = await getSession();
  const currentBotId = await getCurrentBotId();
  const organizations = session?.user.organizations || [];
  const currentOrg = organizations.find((item) => item.id === session?.organizationId) || null;
  const defaultOrg = currentOrg || organizations[0] || null;
  const [behavior, templates, verticals, bots] = await Promise.all([getBotBehavior(), getBotTemplates(), getVerticalCatalog(), getBots()]);
  const selectedBot = bots.find((item) => item.id === currentBotId) || null;
  const selectedVerticalId = selectedBot?.vertical || currentOrg?.vertical || verticals[0]?.id;
  const selectedVertical = selectedVerticalId ? await getVerticalProfile(selectedVerticalId) : null;
  const simulationCases: Array<{ id: string; name: string; expected_signal?: string | null }> = selectedBot
    ? (await getBotSimulationCases(selectedBot.id)).map((item) => ({
        id: typeof item?.id === "string" ? item.id : String(item?.id ?? ""),
        name: typeof item?.name === "string" ? item.name : "Caso",
        expected_signal: typeof item?.expected_signal === "string" ? item.expected_signal : null,
      })).filter((item) => Boolean(item.id))
    : [];
  const simulationRuns: Array<{ case_name?: string | null; status?: string | null; score?: number | null }> = selectedBot
    ? (await getBotSimulationRuns(selectedBot.id)).map((item) => ({
        case_name: typeof item?.case_name === "string" ? item.case_name : null,
        status: typeof item?.status === "string" ? item.status : null,
        score: typeof item?.score === "number" ? item.score : null,
      }))
    : [];

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
      subtitle="Proceso completo de creación: elige tenant, elige vertical, define el objetivo, nombra el bot y publícalo sin salir de esta vista. El catálogo de verticales siempre queda visible, aunque aún no hayas fijado una organización activa en sesión."
      action={<><Link href="/bots" className="secondary-btn">Ver bots</Link><Link href="/flows" className="secondary-btn">Flujos</Link></>}
    >
      <ContextTip title={currentOrg ? "Proceso listo para crear" : "Catálogo listo, falta elegir tenant"}>
        {currentOrg ? (
          <>
            Estás creando sobre <strong>{currentOrg.name}</strong>. Puedes cambiar la organización dentro del mismo formulario sin perder el catálogo de verticales.
          </>
        ) : (
          <>
            Ya cargamos <strong>{verticals.length} verticales</strong>. El siguiente paso es elegir la organización dentro del formulario; no hace falta salir de esta vista.
          </>
        )}
      </ContextTip>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Modo actual" value={safeText(behavior.bot_mode, "sin definir")} hint="Cómo está operando hoy" icon="bot" tone="green" />
        <StatCard label="Tono" value={safeText(behavior.tone, "sin definir")} hint="Cómo responde al cliente" icon="spark" tone="blue" />
        <StatCard label="Imágenes automáticas" value={yesNo(behavior.auto_send_images)} hint="Si el bot manda imágenes solo" icon="image" tone="gold" />
        <StatCard label="Verticales listas" value={String(verticals.length)} hint="Catálogo madre disponible" icon="layers" tone="slate" />
      </div>

      <Section title="Crear bot nuevo con vertical" subtitle="Flujo punta a punta: 1) elige la organización, 2) elige la vertical, 3) define objetivo y datos base, 4) crea y publica el draft inicial sin cambiar de pantalla." icon="check">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <ModuleCard title="Paso 1" description={defaultOrg ? `Tenant sugerido: ${safeText(defaultOrg.name)}` : "Selecciona la organización donde nacerá el bot."} icon="client" tone="blue" />
          <ModuleCard title="Paso 2" description={`Elige una de las ${verticals.length} verticales disponibles para sembrar comportamiento, templates y defaults.`} icon="layers" tone="green" />
          <ModuleCard title="Paso 3" description="Nombra el negocio, define objetivo y tono para que el primer draft salga alineado a la operación." icon="wand" tone="gold" />
          <ModuleCard title="Paso 4" description="Crea el bot y, si quieres, publícalo de una vez con su primer draft." icon="check" tone="slate" />
        </div>

        <form action={createBotAction} className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label className="field-label">Organización
            <select className="field-input" name="organization_id" defaultValue={session?.organizationId || defaultOrg?.id || ""} required disabled={!organizations.length}>
              {organizations.length ? organizations.map((organization) => (
                <option key={organization.id} value={organization.id}>
                  {organization.name}
                </option>
              )) : <option value="">Sin organizaciones disponibles</option>}
            </select>
          </label>
          <label className="field-label">Vertical madre
            <select className="field-input" name="vertical" defaultValue={defaultOrg?.vertical || selectedVerticalId || verticals[0]?.id || ""} required>
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
            <input className="field-input" name="timezone" defaultValue={currentOrg?.timezone || defaultOrg?.timezone || "America/Mexico_City"} />
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
          <div className="md:col-span-2 xl:col-span-3 flex flex-wrap gap-3">
            <button className="primary-btn" type="submit" disabled={!organizations.length}>Crear bot con vertical</button>
            {!organizations.length ? <Link href="/organizations" className="secondary-btn">Primero crea o asigna una organización</Link> : null}
          </div>
        </form>
      </Section>

      <Section title="Aplicar vertical al bot seleccionado" subtitle="Si ya existe un bot, este formulario reaplica vertical, reescribe comportamiento y reemplaza templates para dejarlo alineado con la nueva operación." icon="wand">
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

      <Section title="Simulador y snapshots" subtitle="Antes de publicar, ya puedes guardar snapshot del draft y correr casos de prueba simples contra el comportamiento esperado del bot." icon="spark">
        {selectedBot && currentOrg ? (
          <div className="grid gap-5 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div className="grid gap-4">
              <form action={createBotDraftSnapshotAction} className="grid gap-3 rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
                <input type="hidden" name="bot_id" value={selectedBot.id} />
                <label className="field-label">Motivo del snapshot
                  <input className="field-input" name="reason" placeholder="Antes de editar tono y ventas" />
                </label>
                <button type="submit" className="primary-btn">Guardar snapshot</button>
              </form>
              <form action={createBotSimulationCaseAction} className="grid gap-3 rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
                <input type="hidden" name="bot_id" value={selectedBot.id} />
                <label className="field-label">Caso de prueba
                  <input className="field-input" name="name" placeholder="Lead que pide precio y horario" required />
                </label>
                <label className="field-label">Mensaje entrante
                  <textarea className="field-input min-h-[120px]" name="prompt" placeholder="Hola, quiero saber cuánto cuesta una limpieza y si tienen citas mañana." required />
                </label>
                <label className="field-label">Señal esperada
                  <input className="field-input" name="expected_signal" placeholder="pricing_then_booking" />
                </label>
                <button type="submit" className="primary-btn">Guardar caso</button>
              </form>
              <form action={runBotSimulationAction} className="grid gap-3 rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5">
                <input type="hidden" name="bot_id" value={selectedBot.id} />
                <label className="field-label">Caso a ejecutar
                  <select className="field-input" name="case_id" defaultValue={simulationCases[0]?.id || ""} required>
                    {simulationCases.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                </label>
                <button type="submit" className="primary-btn" disabled={!simulationCases.length}>Correr simulación</button>
              </form>
            </div>
            <div className="grid gap-4">
              <ModuleCard title="Casos guardados" description={simulationCases.map((item) => `${safeText(item.name)} · ${safeText(item.expected_signal, "sin señal")}`).join("\n") || "Todavía no guardas casos."} icon="check" tone="blue" />
              <ModuleCard title="Corridas recientes" description={simulationRuns.map((item) => `${safeText(item.case_name)} · ${safeText(item.status)} · ${safeText(item.score?.toString(), "sin score")}`).join("\n") || "Todavía no hay corridas."} icon="play" tone="gold" />
              <ModuleCard title="Templates base" description={templates.slice(0, 6).map((item) => safeText(item.name)).join(" · ") || "Sin templates disponibles"} icon="chat" tone="slate" />
            </div>
          </div>
        ) : (
          <EmptyActionState title="Selecciona o crea un bot primero" description="El simulador necesita un bot activo y una organización resuelta para poder comparar snapshots, casos y corridas." primaryAction={<Link href="/bots" className="primary-btn">Ir a bots</Link>} />
        )}
      </Section>
    </Shell>
  );
}
