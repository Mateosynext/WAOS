export type VerticalKey = "general" | "health" | "retail" | "services";

export type ThemeConfig = {
  key: VerticalKey;
  label: string;
  accent: "green" | "blue" | "gold";
  accentHex: string;
  accentSoft: string;
  accentStrong: string;
  eyebrow: string;
  promise: string;
  cta: string;
  scenario: string;
};

export const verticalThemes: Record<VerticalKey, ThemeConfig> = {
  general: { key: "general", label: "Operacion general", accent: "green", accentHex: "#00E676", accentSoft: "rgba(0,230,118,0.12)", accentStrong: "rgba(0,230,118,0.22)", eyebrow: "AFTER HOURS COMMERCE", promise: "Responde, vende y controla conversaciones en segundos.", cta: "Quiero ver WAOS en vivo", scenario: "Sistema comercial nocturno para convertir conversaciones mientras duermes." },
  health: { key: "health", label: "Salud y clinicas", accent: "blue", accentHex: "#5BC8FF", accentSoft: "rgba(91,200,255,0.12)", accentStrong: "rgba(91,200,255,0.22)", eyebrow: "MEDICAL RESPONSE SYSTEM", promise: "Agenda, confirma y prepara citas sin friccion.", cta: "Quiero llenar agenda", scenario: "WAOS responde, precalifica y agenda con tono claro y controlado para salud." },
  retail: { key: "retail", label: "Retail y pagos", accent: "gold", accentHex: "#F5C842", accentSoft: "rgba(245,200,66,0.12)", accentStrong: "rgba(245,200,66,0.22)", eyebrow: "REVENUE ENGINE", promise: "Convierte preguntas de precio en cierres y pagos.", cta: "Quiero mover inventario", scenario: "WAOS empuja promo, bundle y urgencia controlada para retail y cobros." },
  services: { key: "services", label: "Servicios premium", accent: "green", accentHex: "#00E676", accentSoft: "rgba(0,230,118,0.12)", accentStrong: "rgba(0,230,118,0.22)", eyebrow: "SERVICE BOOKING MODE", promise: "Muestra valor, agenda rapido y sostiene seguimiento.", cta: "Quiero llenar agenda premium", scenario: "WAOS responde con claridad, muestra expertise y empuja cita o siguiente paso en menos fricción." },
};

export type StudioVariant = "hero" | "proof" | "close";
export const studioVariants: Record<StudioVariant, { label: string; headline: string; support: string; kpi: string; proof: string; cta: string }> = {
  hero: { label: "Promesa", headline: "Tu negocio trabajando mientras duermes.", support: "WAOS responde, muestra ficha, activa promo y cierra sin dejar conversaciones en visto.", kpi: "24/7", proof: "Atiende despues de horario sin aumentar headcount.", cta: "Manda HOLA" },
  proof: { label: "Prueba", headline: "47 mensajes sin contestar.", support: "47 clientes que ya pudieron comprar en otro lado. WAOS responde en segundos y recupera control.", kpi: "47", proof: "El sistema convierte tiempos muertos en ventas o citas confirmadas.", cta: "Quiero recuperar ventas" },
  close: { label: "Cierre", headline: "Responde. Convierte. Cobra.", support: "Presenta valor, detecta intencion y empuja el siguiente paso con CTA claro y sin ruido.", kpi: "+32%", proof: "Secuencia orientada a cierre con promo, stock y seguimiento visibles.", cta: "Quiero ver el flujo" },
};

export type FlowScenarioKey = "catalog" | "appointment" | "reactivation";
export const flowScenarios: Record<FlowScenarioKey, { label: string; description: string; steps: Array<{ id: string; title: string; detail: string; user: string; bot: string; outcome: string }>; }> = {
  catalog: { label: "Catalogo + cierre", description: "Flujo para descubrir producto, resolver objecion de precio y cerrar con CTA directo.", steps: [
    { id: "intent", title: "Intencion", detail: "El lead pregunta por fotos, specs y precio.", user: "Hola, quiero ver el modelo negro y saber precio.", bot: "Claro. Te comparto foto principal, especificaciones clave y precio actualizado.", outcome: "WAOS detecta producto e interes comercial." },
    { id: "offer", title: "Oferta", detail: "El bot muestra ficha enriquecida y promo si aplica.", user: "Si, y si hay promo mejor.", bot: "Tengo promo activa hoy. Te paso el precio promocional y te lo aparto si quieres.", outcome: "Se reduce friccion y sube urgencia controlada." },
    { id: "close", title: "Cierre", detail: "Se empuja el siguiente paso directo.", user: "Va, me interesa.", bot: "Perfecto. Te mando link de pago o si prefieres te lo aparto ahora mismo.", outcome: "Conversacion lista para pago o apartado." },
  ] },
  appointment: { label: "Agenda guiada", description: "Flujo de servicio para calificar, proponer horario y confirmar cita desde WhatsApp.", steps: [
    { id: "prequal", title: "Precalificacion", detail: "Se entiende el servicio y se filtra la necesidad.", user: "Quiero agendar una valoracion esta semana.", bot: "Te ayudo. Dime si prefieres manana o tarde y te comparto opciones.", outcome: "WAOS captura datos sin saturar el chat." },
    { id: "slot", title: "Slot", detail: "Se proponen opciones reales y sucursal.", user: "Manana en la tarde.", bot: "Tengo jueves 4:00 pm y viernes 5:30 pm en Polanco. ¿Cual te aparto?", outcome: "La cita se vuelve concreta y accionable." },
    { id: "confirm", title: "Confirmacion", detail: "Se cierra con tarjeta de cita e instrucciones.", user: "Jueves 4:00 pm.", bot: "Listo. Tu cita queda confirmada para jueves 4:00 pm. Te mando ubicacion y preparacion previa.", outcome: "Agenda confirmada con menos fuga." },
  ] },
  reactivation: { label: "Reactivacion", description: "Flujo para recuperar conversaciones frias con prueba, urgencia y CTA unico.", steps: [
    { id: "nudge", title: "Nudge", detail: "Se reactiva con contexto corto y directo.", user: "(lead sin respuesta 48h)", bot: "Hola. Te dejo aqui la opcion que viste y la promo vigente por si aun te interesa.", outcome: "Se reabre la conversacion sin friccion." },
    { id: "proof", title: "Prueba", detail: "Se resuelve objecion con valor o evidencia.", user: "Si me interesa, pero sigo viendo opciones.", bot: "Te comparto por que este paquete se mueve mas: mejor margen de valor, entrega rapida y promo activa hoy.", outcome: "Se sostiene interes con argumento util." },
    { id: "action", title: "Accion", detail: "Se deja un CTA unico para cerrar.", user: "Ok.", bot: "Si quieres, te lo aparto ahora y te mando el siguiente paso en un mensaje.", outcome: "Listo para cierre o escalamiento humano." },
  ] },
};

export function getVerticalTheme(raw?: string | null): ThemeConfig { if (!raw) return verticalThemes.general; const key = raw.toLowerCase() as VerticalKey; return verticalThemes[key] || verticalThemes.general; }
export function getStudioVariant(raw?: string | null) { if (!raw) return studioVariants.hero; const key = raw.toLowerCase() as StudioVariant; return studioVariants[key] || studioVariants.hero; }
export function getFlowScenario(raw?: string | null) { if (!raw) return flowScenarios.catalog; const key = raw.toLowerCase() as FlowScenarioKey; return flowScenarios[key] || flowScenarios.catalog; }
