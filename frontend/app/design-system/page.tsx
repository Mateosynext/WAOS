import { Badge, ModuleCard, Section, Shell, StoryBeat } from "../components";

export default async function DesignSystemPage() {
  return (
    <Shell title="Reglas del frontend" subtitle="Esta pantalla deja claro el criterio visual del producto para que el diseño se mantenga ordenado, legible y profesional en ambos modos.">
      <Section title="Principios de interfaz" subtitle="Todo el producto nuevo se apoya en estas reglas." icon="palette">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ModuleCard title="Lenguaje simple" description="Los títulos y textos deben hablar como tareas reales, no como arquitectura interna." icon="spark" tone="green" />
          <ModuleCard title="Acciones claras" description="Cada pantalla debe dejar claro qué hacer primero y qué se puede posponer." icon="target" tone="blue" />
          <ModuleCard title="Dos modos" description="Super admin para operar; portal cliente para consultar y gestionar lo suyo." icon="client" tone="gold" />
          <ModuleCard title="Menos ruido" description="Evitar módulos duplicados, nombres confusos y pantallas que enseñan de más." icon="layers" tone="slate" />
        </div>
      </Section>
      <Section title="Jerarquía visual" subtitle="La forma de leer la interfaz debe ser la misma en todo el producto." icon="palette">
        <div className="grid gap-4 md:grid-cols-3">
          <StoryBeat step="1" title="Primero el objetivo" description="La parte alta de la pantalla explica qué resuelve esa vista y cuáles son sus acciones principales." outcome="Siempre debe quedar claro para qué sirve la pantalla." tone="green" />
          <StoryBeat step="2" title="Luego el pulso" description="Después van métricas o tarjetas que ayuden a orientarse rápido." outcome="El usuario entiende la situación sin meterse a detalle técnico." tone="blue" />
          <StoryBeat step="3" title="Luego el trabajo" description="Al final aparecen tablas, listas o bloques de operación con contexto suficiente." outcome="La parte operativa llega cuando ya se entiende el panorama." tone="gold" />
        </div>
      </Section>
      <Section title="Estados base" subtitle="Etiquetas de estado usadas en todo el producto." icon="check">
        <div className="flex flex-wrap gap-2"><Badge tone="green">estable</Badge><Badge tone="amber">requiere atención</Badge><Badge tone="red">con problema</Badge><Badge tone="sky">en proceso</Badge><Badge tone="slate">informativo</Badge></div>
      </Section>
    </Shell>
  );
}
