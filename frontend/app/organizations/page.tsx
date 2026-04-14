import { switchOrganizationAction, updateOrganizationVerticalAction } from "../actions";
import OrganizationSwitcher from "../components/OrganizationSwitcher";
import { EmptyActionState, ModuleCard, Section, Shell, StatCard, SuccessState } from "../components";
import { getSession } from "../lib/session";
import { safeText } from "../lib/ui";
import { getVerticalCatalog, getVerticalProfile } from "../lib/waos";

export default async function OrganizationsPage() {
  const session = await getSession();
  const organizations = session?.user.organizations || [];
  const selectedOrg = organizations.find((item) => item.id === session?.organizationId) || null;
  const [verticals, currentVertical] = await Promise.all([
    getVerticalCatalog(),
    getVerticalProfile(selectedOrg?.vertical),
  ]);

  return (
    <Shell title="Seleccionar organizacion" subtitle="Fija una organizacion explicita antes de operar y ahora tambien puedes aplicar una vertical madre real al tenant activo sin tocar codigo.">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Organizaciones visibles" value={String(organizations.length)} hint="Contextos a los que esta cuenta puede entrar" icon="client" tone="green" />
        <StatCard label="Verticales madre" value={String(verticals.length)} hint="Catalogo habilitado para super admin" icon="layers" tone="blue" />
        <StatCard label="Tenant activo" value={safeText(selectedOrg?.name, "sin seleccionar")} hint="Sobre este tenant se aplican los cambios" icon="target" tone="gold" />
        <StatCard label="Vertical actual" value={safeText(currentVertical.short_name || currentVertical.name, "sin definir")} hint="Perfil operativo guardado en la organizacion" icon="wand" tone="slate" />
      </div>

      <Section title="Contexto de trabajo" subtitle="Elige una organizacion para cargar bots, integraciones, inbox y releases con el contexto correcto." icon="client">
        {organizations.length ? (
          <OrganizationSwitcher organizations={organizations.map((item) => ({ id: item.id, name: item.name }))} selectedId={session?.organizationId || null} redirectTo="/organizations" action={switchOrganizationAction} />
        ) : (
          <EmptyActionState title="No hay organizaciones disponibles" description="Esta cuenta todavia no tiene organizaciones asignadas o no pudimos cargarlas." />
        )}
      </Section>

      <Section title="Aplicar vertical al tenant activo" subtitle="Este formulario actualiza la organizacion seleccionada y deja persistida la vertical madre para onboarding, super admin y portal cliente." icon="wand">
        {selectedOrg ? (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
            <form action={updateOrganizationVerticalAction} className="grid gap-4 md:grid-cols-2">
              <input type="hidden" name="organization_id" value={selectedOrg.id} />
              <input type="hidden" name="redirect_to" value="/organizations" />
              <label className="field-label">Organizacion
                <input className="field-input" value={selectedOrg.name} readOnly />
              </label>
              <label className="field-label">Vertical madre
                <select className="field-input" name="vertical" defaultValue={selectedOrg.vertical || ""} required>
                  <option value="">Selecciona una vertical</option>
                  {verticals.map((vertical) => <option key={vertical.id} value={vertical.id}>{vertical.name}</option>)}
                </select>
              </label>
              <div className="md:col-span-2">
                <button className="primary-btn" type="submit">Guardar vertical del tenant</button>
              </div>
            </form>
            <SuccessState title={safeText(currentVertical.name, "Vertical lista")} description={safeText(currentVertical.problem, "En cuanto guardes, la organizacion queda alineada con el lenguaje y la operacion de esa vertical.")} />
          </div>
        ) : (
          <EmptyActionState title="Primero selecciona una organizacion" description="Sin un tenant activo no conviene aplicar verticales porque el cambio debe quedar atado a una organizacion real." />
        )}
      </Section>

      <Section title="Verticales madre habilitadas para super admin" subtitle="Este catalogo ya existe en backend y frontend para que el onboarding, la creacion de bot y el portal cliente hablen el mismo idioma operativo." icon="layers">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {verticals.map((vertical) => (
            <ModuleCard
              key={vertical.id}
              title={vertical.name}
              description={vertical.description || vertical.problem || "Vertical lista para operar."}
              icon="wand"
              tone="green"
              footer={<span className="mono-pill">{vertical.recommended_integrations.join(" · ") || "base operativa"}</span>}
            />
          ))}
        </div>
      </Section>
    </Shell>
  );
}
