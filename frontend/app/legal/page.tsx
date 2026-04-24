import Link from "next/link";
import { Shell } from "@/app/components/layout/shell";
import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import { Badge } from "@/app/components/primitives/shared";
import { legalOwner, legalProduct, publicLegalDocs } from "./legal-registry";

export default async function LegalCenterPage() {
  const categories = [...new Set(publicLegalDocs.map((item) => item.category))];
  return (
    <Shell
      title="Centro legal"
      subtitle="Repositorio público de documentos legales, privacidad, seguridad y operación asociados a WAOS."
      action={<Link href="/policies" className="secondary-btn">Volver a políticas</Link>}
    >
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Documentos públicos" value={publicLegalDocs.length} hint="Listos para consulta y versionado" icon="folder" tone="blue" />
        <StatCard label="Categorías cubiertas" value={categories.length} hint="Privacidad, contratación, IA, seguridad y operación" icon="layers" tone="green" />
        <StatCard label="Titular documental" value={legalOwner} hint="Base integrada a nombre del responsable indicado" icon="shield" tone="gold" />
      </div>

      <Section title="Resumen ejecutivo" subtitle="Este centro expone los documentos públicos. Los procedimientos internos, matrices y plantillas de evidencia viven en docs/legal dentro del repositorio." icon="shield">
        <div className="rounded-3xl border border-[color:var(--border-soft)] bg-[color:var(--surface-subtle)] p-5 text-sm leading-7 text-[color:var(--text-secondary)]">
          <p><strong className="text-[color:var(--text-primary)]">Producto:</strong> {legalProduct}</p>
          <p><strong className="text-[color:var(--text-primary)]">Titular documental:</strong> {legalOwner}</p>
          <p><strong className="text-[color:var(--text-primary)]">Cobertura pública:</strong> avisos, términos, MSA, DPA, seguridad, cookies, IA, SLA, pagos, portabilidad, integraciones y disclosure de automatización.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {categories.map((category) => <Badge key={category} tone="sky">{category}</Badge>)}
          </div>
        </div>
      </Section>

      <Section title="Documentos disponibles" subtitle="Cada documento conserva slug estable para poder enlazarlo desde onboarding, login, formularios o sitios públicos." icon="folder">
        <div className="grid gap-4 xl:grid-cols-2">
          {publicLegalDocs.map((doc) => (
            <ModuleCard
              key={doc.slug}
              title={doc.title}
              description={`${doc.summary} Audiencia: ${doc.audience}.`}
              tone="slate"
              icon="folder"
              footer={
                <>
                  <Link href={`/legal/${doc.slug}`} className="primary-btn">Abrir documento</Link>
                  <span className="secondary-btn">{doc.category}</span>
                </>
              }
            />
          ))}
        </div>
      </Section>
    </Shell>
  );
}
