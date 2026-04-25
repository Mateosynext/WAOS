import Link from "next/link";
import { Shell } from "@/app/components/layout/shell";
import { ModuleCard, Section, StatCard } from "@/app/components/primitives/cards";
import { DataTable } from "@/app/components/primitives/data-display";
import { acceptCommercialDocumentAction, createCommercialDocumentPaymentAction, draftCommercialDocumentAction, sendCommercialDocumentAction, convertCommercialDocumentToWorkOrderAction } from "@/app/actions/commercial_documents";
import { getCurrentBotId, requireSession } from "../lib/session";
import { formatDateTime, formatMoney, formatNumber, safeText } from "../lib/ui";
import { getBusinessHubOverview, getReactivationRecommendations } from "@/app/lib/data/analytics";
import { getCatalogProducts, getCatalogServices, getCommerceInsights, getCommercialDocuments, getCommercialDocumentsOverview, getCRMLeads, getCRMPipelineSummary, getOrganizationBranding, getPayments, getPromotionRules, getPromotions } from "@/app/lib/data/commerce";
import { getVerticalProfile } from "@/app/lib/data/verticals";

type SearchParams = Record<string, string | string[] | undefined>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

function documentTypeLabel(value: string) {
  const labels: Record<string, string> = { quote: "Presupuesto", work_order: "Orden", receipt: "Recibo", proposal: "Propuesta", warranty: "Garantía" };
  return labels[value] || value;
}

function documentStatusLabel(value: string) {
  const labels: Record<string, string> = {
    draft: "Borrador",
    requires_data: "Faltan datos",
    requires_approval: "Aprobación",
    approved: "Aprobado",
    sent: "Enviado",
    viewed: "Visto",
    accepted: "Aceptado",
    rejected: "Rechazado",
    expired: "Expirado",
    paid: "Pagado",
    converted: "Convertido",
    completed: "Completado",
    cancelled: "Cancelado",
  };
  return labels[value] || value;
}

export default async function BusinessHubPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const params = (await searchParams) || {};
  const tab = first(params.tab) || "resumen";
  const session = await requireSession();
  const currentBotId = await getCurrentBotId();
  const [hub, products, services, promotions, rules, insights, payments, leads, recommendations, pipeline, commercialDocs, commercialDocsOverview, branding] = await Promise.all([
    getBusinessHubOverview(),
    getCatalogProducts(),
    getCatalogServices(),
    getPromotions(),
    getPromotionRules(),
    getCommerceInsights(),
    getPayments(),
    getCRMLeads(),
    getReactivationRecommendations(),
    getCRMPipelineSummary(),
    getCommercialDocuments(),
    getCommercialDocumentsOverview(),
    getOrganizationBranding(),
  ]);

  const currentOrg = session?.user.organizations.find((item) => item.id === session?.organizationId) || null;
  const verticalProfile = currentOrg?.vertical ? await getVerticalProfile(currentOrg.vertical, currentBotId || undefined, currentOrg.subvertical, session?.organizationId || undefined) : null;
  const summary = hub.summary || {};
  const insightSummary = insights.summary || {};
  const paymentTotal = payments.reduce((acc: number, item) => acc + Number(item.amount || 0), 0);
  const docsSummary = commercialDocsOverview.summary || {};

  return (
    <Shell title="Centro comercial" subtitle="Catálogo, promociones, documentos, insights e ingresos ya no viven en productos distintos. Todo comercial se navega desde aquí." action={<Link href="/client/promociones" className="secondary-btn">Ver portal cliente</Link>}>
      <div className="flex flex-wrap gap-2 rounded-3xl border border-white/[0.08] bg-white/[0.03] p-2">
        {[
          ["resumen", "Resumen"],
          ["catalogo", "Catálogo"],
          ["documentos", "Documentos"],
          ["promociones", "Promociones"],
          ["insights", "Insights"],
          ["pipeline", "Pipeline"],
          ["ingresos", "Ingresos"],
        ].map(([id, label]) => <Link key={id} href={`/business-hub?tab=${id}`} className={tab === id ? "primary-btn" : "secondary-btn"}>{label}</Link>)}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Productos" value={formatNumber(Number(summary.products || products.length || 0))} hint="Oferta visible" icon="catalog" tone="blue" />
        <StatCard label="Documentos" value={formatNumber(Number(docsSummary.documents || commercialDocs.length || 0))} hint="Presupuestos, órdenes y recibos" icon="folder" tone="green" />
        <StatCard label="Promociones" value={formatNumber(Number(summary.promotions || promotions.length || 0))} hint="Ofertas activas" icon="promo" tone="gold" />
        <StatCard label="Ingresos" value={formatMoney(paymentTotal, payments[0]?.currency || "MXN")} hint="Cobros visibles" icon="money" tone="green" />
        <StatCard label="Pipeline weighted" value={formatMoney(Number(pipeline.weighted_amount || 0), payments[0]?.currency || "MXN")} hint="Monto ponderado" icon="target" tone="blue" />
      </div>


      {verticalProfile?.id ? (
        <Section title="Comercial conectado a la vertical" subtitle="El pipeline, las ofertas y los documentos ahora se leen con la subvertical activa como contexto comercial real." icon="target">
          <div className="grid gap-4 xl:grid-cols-4">
            <StatCard label="Subvertical" value={safeText(verticalProfile.selected_subvertical?.name, currentOrg?.subvertical || 'sin definir')} hint={safeText(String(verticalProfile.runtime_connection?.surface_focus?.commercial || 'seguimiento'))} icon="wand" tone="green" />
            <StatCard label="Bundle de servicios" value={formatNumber((verticalProfile.selected_subvertical?.service_bundle || []).length)} hint="Servicios que deberían venderse" icon="catalog" tone="blue" />
            <StatCard label="Objeciones foco" value={formatNumber((verticalProfile.selected_subvertical?.objections || []).length)} hint="Objeciones operables" icon="support" tone="gold" />
            <StatCard label="Automations" value={formatNumber((verticalProfile.selected_subvertical?.automation_priorities || []).length)} hint="Secuencias prioritarias" icon="refresh" tone="slate" />
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <ModuleCard title="Promesa comercial" description={safeText(verticalProfile.selected_subvertical?.promise, verticalProfile.ten_x_narrative)} icon="rocket" tone="green" />
            <ModuleCard title="Buyer y motion" description={`${safeText(verticalProfile.selected_subvertical?.buyer, verticalProfile.buyer.primary)} · ${safeText(verticalProfile.selected_subvertical?.growth_motion, 'motion')}`} icon="client" tone="blue" />
            <ModuleCard title="Preguntas de calificación" description={safeText((verticalProfile.selected_subvertical?.qualification_questions || []).join(' • '), 'Sin preguntas')} icon="chat" tone="gold" />
          </div>
        </Section>
      ) : null}

      {tab === "resumen" ? (
        <Section title="Resumen comercial" subtitle="La foto corta de catálogo, documentos, promociones y resultados." icon="briefcase">
          <DataTable columns={["Tema", "Valor"]} rows={[
            ["Productos", formatNumber(products.length)],
            ["Servicios", formatNumber(services.length)],
            ["Documentos comerciales", formatNumber(Number(docsSummary.documents || commercialDocs.length || 0))],
            ["Monto aceptado en documentos", formatMoney(Number(docsSummary.accepted_amount || 0), payments[0]?.currency || "MXN")],
            ["Promociones activas", formatNumber(promotions.length)],
            ["Leads visibles", formatNumber(leads.length)],
            ["Pipeline weighted", formatMoney(Number(pipeline.weighted_amount || 0), payments[0]?.currency || "MXN")],
          ]} />
          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {(pipeline.stages || []).slice(0, 4).map((item, index) => <div key={`${String(item.stage || index)}`} className="surface-row"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">{safeText(String(item.stage || "etapa"))}</div><div className="mt-1 text-lg font-semibold text-white">{formatNumber(Number(item.total || 0))}</div><div className="mt-2 text-xs text-slate-400">Monto {formatMoney(Number(item.amount || 0), payments[0]?.currency || "MXN")}</div></div>)}
          </div>
        </Section>
      ) : null}

      {tab === "catalogo" ? (
        <Section title="Catálogo" subtitle="Productos y servicios en una sola lectura. Estos conceptos ya pueden alimentar Smart Docs." icon="catalog">
          <DataTable columns={["Nombre", "Tipo", "Precio", "Estado"]} rows={[
            ...products.slice(0, 20).map((item) => [safeText(item.name), "Producto", formatMoney(item.promotional_price || item.price, item.currency || "MXN"), safeText(item.inventory?.[0]?.status, "sin dato")]),
            ...services.slice(0, 20).map((item) => [safeText(item.name), "Servicio", formatMoney(item.price, item.currency || "MXN"), safeText(item.branch, "sin dato")]),
          ]} />
        </Section>
      ) : null}

      {tab === "documentos" ? (
        <div className="space-y-6">
          <Section title="WAOS Smart Docs" subtitle="Convierte mensajes en presupuestos, órdenes de trabajo y recibos PDF con marca del negocio, reglas de aprobación, estados y siguiente paso." icon="folder" aside={<Link href="/api/v1/commercial-documents" className="secondary-btn">API</Link>}>
            <div className="grid gap-4 xl:grid-cols-4">
              <StatCard label="Enviados / vistos" value={formatMoney(Number(docsSummary.sent_amount || 0), "MXN")} hint="Monto en documentos activos" icon="money" tone="blue" />
              <StatCard label="Aceptados" value={formatMoney(Number(docsSummary.accepted_amount || 0), "MXN")} hint="Convertidos o pagados" icon="check" tone="green" />
              <StatCard label="Tasa aceptación" value={`${formatNumber(Number(docsSummary.acceptance_rate || 0))}%`} hint="Aceptados sobre documentos" icon="target" tone="gold" />
              <StatCard label="Por aprobar" value={formatNumber(Number(docsSummary.pending_approval || 0))} hint="Requieren humano" icon="alert" tone="red" />
            </div>
            <div className="mt-5 grid gap-4 xl:grid-cols-3">
              <ModuleCard title="Brand Kit activo" description={`${safeText(branding.business_name, currentOrg?.name || "Negocio")} · color ${safeText(branding.primary_color, "#25D366")}. El PDF usa logo, datos y pie de marca cuando están configurados.`} icon="palette" tone="green" />
              <ModuleCard title="Catálogo como cerebro" description="Los productos y servicios del catálogo alimentan partidas, precios, cantidades, preguntas faltantes y motivos de aprobación." icon="catalog" tone="blue" />
              <ModuleCard title="PDF + flujo comercial" description="Cada documento conserva folio, estado, historial, link PDF, anticipo, saldo y transición a orden de trabajo." icon="flow" tone="gold" />
            </div>
          </Section>

          <Section title="Crear borrador rápido" subtitle="Pega la solicitud del cliente y WAOS intentará conectarla con el catálogo. Si faltan datos o precio, queda marcado para revisión." icon="wand">
            <form action={draftCommercialDocumentAction} className="grid gap-3 xl:grid-cols-[1.3fr_0.7fr_0.5fr_auto]">
              <input type="hidden" name="redirect_to" value="/business-hub?tab=documentos" />
              <textarea name="request_text" className="input min-h-28 xl:col-span-1" placeholder="Ej. Cliente quiere mantenimiento a domicilio para 2 aires acondicionados en Providencia y pregunta cuánto cuesta." />
              <div className="grid gap-3">
                <input name="customer_name" className="input" placeholder="Nombre del cliente" />
                <input name="customer_phone" className="input" placeholder="WhatsApp / teléfono" />
              </div>
              <select name="document_type" className="input h-12">
                <option value="quote">Presupuesto</option>
                <option value="work_order">Orden de trabajo</option>
                <option value="receipt">Recibo</option>
                <option value="proposal">Propuesta</option>
              </select>
              <button type="submit" className="primary-btn h-12 self-start">Crear Smart Doc</button>
            </form>
          </Section>

          <Section title="Documentos recientes" subtitle="PDFs comerciales con estados accionables y conversión a operación." icon="folder">
            <DataTable columns={["Folio", "Cliente", "Tipo", "Total", "Estado", "PDF", "Acciones"]} rows={commercialDocs.map((doc) => [
              <div key={`${doc.id}-folio`}><div className="font-semibold">{safeText(doc.folio)}</div><div className="text-xs text-[color:var(--text-muted)]">{formatDateTime(doc.updated_at)}</div></div>,
              safeText(doc.customer_name || doc.customer_phone, "Cliente por confirmar"),
              documentTypeLabel(doc.document_type),
              formatMoney(doc.total, doc.currency || "MXN"),
              <span key={`${doc.id}-status`} className="mono-pill">{documentStatusLabel(doc.status)}</span>,
              <div key={`${doc.id}-pdf`} className="flex flex-wrap gap-2"><a className="secondary-btn" href={`/api/v1/commercial-documents/${encodeURIComponent(doc.id)}/pdf`} target="_blank" rel="noopener">PDF</a>{doc.public_url ? <a className="secondary-btn" href={doc.public_url} target="_blank" rel="noopener">Cliente</a> : null}{doc.payment_url ? <a className="secondary-btn" href={doc.payment_url} target="_blank" rel="noopener">Pago</a> : null}</div>,
              <div key={`${doc.id}-actions`} className="flex flex-wrap gap-2">
                {doc.status !== "sent" ? (
                  <form action={sendCommercialDocumentAction}>
                    <input type="hidden" name="document_id" value={doc.id} />
                    <input type="hidden" name="redirect_to" value="/business-hub?tab=documentos" />
                    <button type="submit" className="secondary-btn">Enviar WA</button>
                  </form>
                ) : null}
                {doc.document_type === "quote" && !["accepted", "paid", "converted"].includes(doc.status) ? (
                  <form action={acceptCommercialDocumentAction}>
                    <input type="hidden" name="document_id" value={doc.id} />
                    <input type="hidden" name="redirect_to" value="/business-hub?tab=documentos" />
                    <button type="submit" className="secondary-btn">Aceptar</button>
                  </form>
                ) : null}
                {doc.document_type === "quote" && doc.total > 0 && !doc.payment_url ? (
                  <form action={createCommercialDocumentPaymentAction}>
                    <input type="hidden" name="document_id" value={doc.id} />
                    <input type="hidden" name="redirect_to" value="/business-hub?tab=documentos" />
                    <button type="submit" className="secondary-btn">Anticipo</button>
                  </form>
                ) : null}
                {doc.document_type === "quote" && doc.status !== "converted" ? (
                  <form action={convertCommercialDocumentToWorkOrderAction}>
                    <input type="hidden" name="document_id" value={doc.id} />
                    <input type="hidden" name="redirect_to" value="/business-hub?tab=documentos" />
                    <button type="submit" className="secondary-btn">Crear OT</button>
                  </form>
                ) : null}
              </div>,
            ])} />
          </Section>

          <Section title="Recomendaciones Smart Docs" subtitle="La capa de documentos no es decorativa: debe cerrar, cobrar y activar operación." icon="spark">
            <div className="grid gap-4 md:grid-cols-3">
              {commercialDocsOverview.recommendations.map((item, index) => <ModuleCard key={item} title={`Recomendación ${index + 1}`} description={item} icon="check" tone={index === 0 ? "green" : index === 1 ? "blue" : "gold"} />)}
            </div>
          </Section>
        </div>
      ) : null}

      {tab === "promociones" ? (
        <Section title="Promociones" subtitle="Ofertas y reglas comerciales sin brincar de pantalla." icon="promo">
          <DataTable columns={["Promoción", "Vigencia", "CTA", "Regla"]} rows={promotions.map((item, index) => [safeText(item.name), `${safeText(item.starts_at)} → ${safeText(item.ends_at)}`, safeText(item.cta_label), safeText(rules[index]?.name || rules[index]?.condition || "sin regla")])} />
        </Section>
      ) : null}

      {tab === "insights" ? (
        <Section title="Insights comerciales" subtitle="Qué vende, qué frena y qué conviene tocar primero." icon="stats">
          <DataTable columns={["Tema", "Valor"]} rows={[
            ["Ingresos", formatMoney(Number(insightSummary.revenue || 0), safeText(insightSummary.currency, "MXN"))],
            ["Conversión", safeText(insightSummary.conversion_rate ? `${insightSummary.conversion_rate}%` : null, "-")],
            ["Pedidos", formatNumber(Number(insightSummary.orders || 0))],
            ["Alertas", formatNumber((insights.alerts || []).length)],
          ]} />
        </Section>
      ) : null}


      {tab === "pipeline" ? (
        <Section title="Pipeline y motivos de pérdida" subtitle="Resumen comercial accionable por etapa, monto y pérdida estructurada." icon="target">
          <DataTable columns={["Etapa", "Leads", "Monto", "Prob. cierre"]} rows={(pipeline.stages || []).map((item) => [safeText(String(item.stage || "etapa")), formatNumber(Number(item.total || 0)), formatMoney(Number(item.amount || 0), payments[0]?.currency || "MXN"), `${formatNumber(Number(item.avg_close_probability || 0))}%`])} />
          <div className="mt-5 grid gap-4 xl:grid-cols-2">
            <div>
              <div className="eyebrow mb-3">Motivos de pérdida</div>
              <DataTable columns={["Motivo", "Total"]} rows={(pipeline.lost_reasons || []).map((item) => [safeText(String(item.lost_reason || "sin_motivo")), formatNumber(Number(item.total || 0))])} />
            </div>
            <div>
              <div className="eyebrow mb-3">Cambios recientes de etapa</div>
              <DataTable columns={["Lead", "De", "A", "Fecha"]} rows={(pipeline.recent_stage_changes || []).slice(0, 10).map((item) => [safeText(String(item.crm_lead_id || item.id || "lead")), safeText(String(item.previous_stage || "-")), safeText(String(item.new_stage || "-")), safeText(String(item.created_at || "-"))])} />
            </div>
          </div>
        </Section>
      ) : null}

      {tab === "ingresos" ? (
        <Section title="Ingresos y reactivación" subtitle="Pagos, leads y recomendaciones de reactivación en una sola capa." icon="money">
          <DataTable columns={["Tema", "Detalle"]} rows={[
            ...payments.slice(0, 10).map((item) => [safeText(item.id || item.reference), `${formatMoney(item.amount, item.currency || "MXN")} · ${safeText(item.status)}`]),
            ...recommendations.slice(0, 10).map((item) => [safeText(item.contact_name || item.id), safeText(item.next_step || item.reason)]),
          ]} />
        </Section>
      ) : null}
    </Shell>
  );
}
