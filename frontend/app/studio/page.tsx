import Link from "next/link";
import { ModuleCard, Section, SegmentedLinks, Shell, WhatsAppPreview } from "../components";

const verticals = [
  { key: 'retail', label: 'Retail', tone: 'green' as const, description: 'Venta de catálogo, promociones y seguimiento comercial.' },
  { key: 'beauty', label: 'Beauty', tone: 'gold' as const, description: 'Agenda, servicios, promociones y recuperación de leads.' },
  { key: 'education', label: 'Education', tone: 'blue' as const, description: 'Asesoría, seguimiento y captación ordenada.' },
];

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

export default async function StudioPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const selected = verticals.find((item) => item.key === first(params.vertical)) || verticals[0];
  return (
    <Shell title="Studio" subtitle="Una vista guiada para explicar el valor del bot con un relato simple, ordenado y fácil de presentar." action={<Link href="/client" className="secondary-btn">Ver portal cliente</Link>}>
      <Section title="Escenario guiado" subtitle="Cambia de vertical para presentar una historia más cercana al negocio del cliente." icon="play">
        <SegmentedLinks items={verticals.map((item) => ({ href: `/studio?vertical=${item.key}`, label: item.label, active: item.key === selected.key }))} />
      </Section>
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Section title="Qué demuestra esta vista" subtitle={selected.description} icon="target">
          <div className="grid gap-4 md:grid-cols-2">
            <ModuleCard title="Crear confianza" description="Mostrar una conversación clara, con información útil y sin tono robótico." icon="chat" tone="green" />
            <ModuleCard title="Mover a la acción" description="Cerrar con siguiente paso visible: agendar, comprar o dejar solicitud." icon="target" tone="blue" />
            <ModuleCard title="Explicar valor" description="Hacer visible cómo el bot ahorra tiempo al equipo y le da claridad al cliente." icon="spark" tone="gold" />
            <ModuleCard title="Hacerlo creíble" description="Se ve como un producto listo, no como una prueba improvisada." icon="check" tone="slate" />
          </div>
        </Section>
        <WhatsAppPreview
          title={`Vista ${selected.label}`}
          scenario={selected.description}
          userPrompt="Hola, quiero saber si este bot me puede ayudar hoy mismo."
          themeTone={selected.tone}
          objective="Mostrar una experiencia comprensible, amable y orientada a resultado desde el primer mensaje."
          proofLabel="VISTA"
          highlights={[
            'Arranca con una respuesta clara y útil.',
            'Explica qué puede hacer sin saturar al cliente.',
            'Cierra con una acción concreta y fácil de entender.',
          ]}
          quickReplies={['Quiero información', 'Agendar', 'Hablar con alguien']}
          blocks={[
            { type: 'text', text: 'Sí, puedo ayudarte a resolverlo hoy. Primero te explico rápido y luego te doy el siguiente paso.' },
            { type: 'text', text: 'Te mostraré opciones, disponibilidad y, si quieres, lo dejo encaminado de una vez.' },
            { type: 'cta', label: 'Continuar' },
          ]}
          footer="La vista muestra una conversación clara, breve y orientada a resultado."
        />
      </div>
    </Shell>
  );
}
