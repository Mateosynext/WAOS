"use client";

import { useMemo, useState } from "react";
import { sendConversationMessageAction } from "../actions";

type ComposerMode =
  | "text"
  | "note"
  | "image"
  | "audio"
  | "document"
  | "video"
  | "template"
  | "interactive_button"
  | "interactive_list"
  | "flow_entrypoint"
  | "product"
  | "catalog"
  | "mark_as_read";

type ButtonDraft = { id: string; title: string };
type ListRowDraft = { section: string; id: string; title: string; description: string };

type ComposerResult = {
  kind: "text" | "note";
  body: string;
  whatsappPayload?: Record<string, unknown>;
  errors: string[];
};

const QUICK_REPLIES = [
  "Hola, ya estoy revisando tu caso y te respondo con claridad en un momento.",
  "Gracias por escribir. ¿Me confirmas el pedido, cita o tema exacto para ayudarte más rápido?",
  "Ya tomé este caso manualmente. Te acompaño por aquí hasta cerrarlo.",
  "Entendido. Voy a verificarlo y te comparto el siguiente paso hoy mismo.",
];

const MAX_BUTTONS = 3;

const SNIPPETS = [
  { label: "Seguimiento", value: "Dame unos minutos para revisarlo y te confirmo por aquí el siguiente paso." },
  { label: "Agendar", value: "¿Qué horario te funciona mejor? Te comparto opciones en cuanto me confirmes." },
  { label: "Cobro", value: "Voy a revisar el estatus del cobro y te actualizo con la referencia exacta." },
];

const MODE_LABELS: Array<{ value: ComposerMode; label: string; hint: string }> = [
  { value: "text", label: "Texto", hint: "Respuesta clásica" },
  { value: "note", label: "Nota interna", hint: "No sale al cliente" },
  { value: "image", label: "Imagen", hint: "Link o media ID" },
  { value: "audio", label: "Audio", hint: "Nota o clip" },
  { value: "document", label: "Documento", hint: "PDF, DOC, XLS" },
  { value: "video", label: "Video", hint: "Media saliente" },
  { value: "template", label: "Template", hint: "Plantilla aprobada" },
  { value: "interactive_button", label: "Botones", hint: "Reply buttons" },
  { value: "interactive_list", label: "Lista", hint: "Menú interactivo" },
  { value: "flow_entrypoint", label: "Flow", hint: "Entrypoint de Flow" },
  { value: "product", label: "Producto", hint: "Single product" },
  { value: "catalog", label: "Catálogo", hint: "Multi-product" },
  { value: "mark_as_read", label: "Marcar leído", hint: "Status técnico" },
];

function compact(value: string) {
  return value.trim();
}

function buildTemplateParameters(raw: string) {
  return raw
    .split("\n")
    .map((item) => compact(item))
    .filter(Boolean)
    .map((text) => ({ type: "text", text }));
}

function groupListRows(rows: ListRowDraft[]) {
  const grouped = new Map<string, Array<{ id: string; title: string; description?: string }>>();
  rows.forEach((row) => {
    const section = compact(row.section) || "Opciones";
    const current = grouped.get(section) || [];
    current.push({
      id: compact(row.id),
      title: compact(row.title),
      description: compact(row.description) || undefined,
    });
    grouped.set(section, current);
  });
  return Array.from(grouped.entries()).map(([title, sectionRows]) => ({ title, rows: sectionRows }));
}

export default function ConversationComposer({ conversationId, redirectTo }: { conversationId: string; redirectTo: string }) {
  const [mode, setMode] = useState<ComposerMode>("text");
  const [body, setBody] = useState("");
  const [mediaSourceType, setMediaSourceType] = useState<"link" | "id">("link");
  const [mediaRef, setMediaRef] = useState("");
  const [mediaCaption, setMediaCaption] = useState("");
  const [mediaFilename, setMediaFilename] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [templateLanguageCode, setTemplateLanguageCode] = useState("es_MX");
  const [templateBodyParams, setTemplateBodyParams] = useState("");
  const [interactiveBody, setInteractiveBody] = useState("");
  const [interactiveFooter, setInteractiveFooter] = useState("");
  const [buttons, setButtons] = useState<ButtonDraft[]>([
    { id: "confirmar", title: "Confirmar" },
    { id: "hablar_humano", title: "Hablar con asesor" },
  ]);
  const [listButtonLabel, setListButtonLabel] = useState("Ver opciones");
  const [listRows, setListRows] = useState<ListRowDraft[]>([
    { section: "Opciones", id: "opcion_1", title: "Plan Premium", description: "Con asesor" },
    { section: "Opciones", id: "opcion_2", title: "Agendar llamada", description: "15 minutos" },
  ]);
  const [flowId, setFlowId] = useState("");
  const [flowToken, setFlowToken] = useState("");
  const [flowCta, setFlowCta] = useState("Abrir flujo");
  const [flowBody, setFlowBody] = useState("Completa tu pre-registro");
  const [flowFooter, setFlowFooter] = useState("");
  const [productCatalogId, setProductCatalogId] = useState("");
  const [productRetailerId, setProductRetailerId] = useState("");
  const [productBody, setProductBody] = useState("Te comparto este producto.");
  const [productFooter, setProductFooter] = useState("");
  const [catalogId, setCatalogId] = useState("");
  const [catalogBody, setCatalogBody] = useState("Estos son los productos disponibles");
  const [catalogSectionTitle, setCatalogSectionTitle] = useState("Destacados");
  const [catalogProducts, setCatalogProducts] = useState("sku-1\nsku-2");
  const [markAsReadTarget, setMarkAsReadTarget] = useState("");

  const composer = useMemo<ComposerResult>(() => {
    const errors: string[] = [];

    if (mode === "note") {
      if (!compact(body)) errors.push("La nota interna necesita texto.");
      return { kind: "note", body: body, errors };
    }

    if (mode === "text") {
      if (!compact(body)) errors.push("El mensaje de texto necesita contenido.");
      return { kind: "text", body, errors };
    }

    if (["image", "audio", "document", "video"].includes(mode)) {
      if (!compact(mediaRef)) errors.push("Necesitas un link o media ID.");
      const media: Record<string, string> = { [mediaSourceType]: compact(mediaRef) };
      if (compact(mediaCaption)) media.caption = compact(mediaCaption);
      if (mode === "document" && compact(mediaFilename)) media.filename = compact(mediaFilename);
      return {
        kind: "text",
        body: compact(mediaCaption) || body,
        whatsappPayload: { message_type: mode, media },
        errors,
      };
    }

    if (mode === "template") {
      if (!compact(templateName)) errors.push("El template necesita nombre.");
      const parameters = buildTemplateParameters(templateBodyParams);
      return {
        kind: "text",
        body: body,
        whatsappPayload: {
          message_type: "template",
          template: {
            name: compact(templateName),
            language: { code: compact(templateLanguageCode) || "es_MX" },
            components: parameters.length ? [{ type: "body", parameters }] : [],
          },
        },
        errors,
      };
    }

    if (mode === "interactive_button") {
      const activeButtons = buttons.map((item) => ({ id: compact(item.id), title: compact(item.title) })).filter((item) => item.id || item.title);
      if (!compact(interactiveBody)) errors.push("Los botones necesitan texto principal.");
      if (!activeButtons.length) errors.push("Agrega al menos un botón.");
      if (activeButtons.length > MAX_BUTTONS) errors.push("WhatsApp solo permite hasta 3 botones.");
      if (activeButtons.some((item) => !item.id || !item.title)) errors.push("Cada botón necesita id y título.");
      return {
        kind: "text",
        body: interactiveBody,
        whatsappPayload: {
          message_type: "interactive_button",
          interactive: {
            body: { text: compact(interactiveBody) },
            footer: compact(interactiveFooter) ? { text: compact(interactiveFooter) } : undefined,
            buttons: activeButtons,
          },
        },
        errors,
      };
    }

    if (mode === "interactive_list") {
      const activeRows = listRows
        .map((row) => ({ section: compact(row.section), id: compact(row.id), title: compact(row.title), description: compact(row.description) }))
        .filter((row) => row.id || row.title || row.description);
      if (!compact(interactiveBody)) errors.push("La lista necesita texto principal.");
      if (!compact(listButtonLabel)) errors.push("La lista necesita etiqueta de botón.");
      if (!activeRows.length) errors.push("Agrega al menos una fila a la lista.");
      if (activeRows.some((row) => !row.id || !row.title)) errors.push("Cada fila necesita id y título.");
      return {
        kind: "text",
        body: interactiveBody,
        whatsappPayload: {
          message_type: "interactive_list",
          interactive: {
            body: { text: compact(interactiveBody) },
            footer: compact(interactiveFooter) ? { text: compact(interactiveFooter) } : undefined,
            button: compact(listButtonLabel),
            sections: groupListRows(activeRows),
          },
        },
        errors,
      };
    }

    if (mode === "flow_entrypoint") {
      if (!compact(flowId)) errors.push("El flow necesita flow_id.");
      if (!compact(flowBody)) errors.push("El flow necesita body visible.");
      return {
        kind: "text",
        body: flowBody,
        whatsappPayload: {
          message_type: "flow_entrypoint",
          flow: {
            flow_id: compact(flowId),
            flow_token: compact(flowToken) || undefined,
            flow_cta: compact(flowCta) || "Abrir",
            body: { text: compact(flowBody) },
            footer: compact(flowFooter) ? { text: compact(flowFooter) } : undefined,
          },
        },
        errors,
      };
    }

    if (mode === "product") {
      if (!compact(productCatalogId)) errors.push("El producto necesita catalog_id.");
      if (!compact(productRetailerId)) errors.push("El producto necesita product_retailer_id.");
      return {
        kind: "text",
        body: productBody,
        whatsappPayload: {
          message_type: "product",
          product: {
            catalog_id: compact(productCatalogId),
            product_retailer_id: compact(productRetailerId),
            body: { text: compact(productBody) || "Te comparto este producto." },
            footer: compact(productFooter) ? { text: compact(productFooter) } : undefined,
          },
        },
        errors,
      };
    }

    if (mode === "catalog") {
      const productItems = catalogProducts.split("\n").map((item) => compact(item)).filter(Boolean);
      if (!compact(catalogId)) errors.push("El catálogo necesita catalog_id.");
      if (!productItems.length) errors.push("El catálogo necesita al menos un SKU.");
      return {
        kind: "text",
        body: catalogBody,
        whatsappPayload: {
          message_type: "catalog",
          catalog: {
            catalog_id: compact(catalogId),
            body: { text: compact(catalogBody) || "Estos son los productos disponibles" },
            sections: [
              {
                title: compact(catalogSectionTitle) || "Destacados",
                product_items: productItems.map((product_retailer_id) => ({ product_retailer_id })),
              },
            ],
          },
        },
        errors,
      };
    }

    if (mode === "mark_as_read") {
      if (!compact(markAsReadTarget)) errors.push("Necesitas el message_id a marcar como leído.");
      return {
        kind: "text",
        body: "",
        whatsappPayload: {
          message_type: "mark_as_read",
          read_target: compact(markAsReadTarget),
        },
        errors,
      };
    }

    return { kind: "text", body, errors: ["Modo no soportado en el composer."] };
  }, [
    body,
    buttons,
    catalogBody,
    catalogId,
    catalogProducts,
    catalogSectionTitle,
    flowBody,
    flowCta,
    flowFooter,
    flowId,
    flowToken,
    interactiveBody,
    interactiveFooter,
    listButtonLabel,
    listRows,
    markAsReadTarget,
    mediaCaption,
    mediaFilename,
    mediaRef,
    mediaSourceType,
    mode,
    productBody,
    productCatalogId,
    productFooter,
    productRetailerId,
    templateBodyParams,
    templateLanguageCode,
    templateName,
  ]);

  const previewJson = composer.whatsappPayload ? JSON.stringify(composer.whatsappPayload, null, 2) : "Sin payload estructurado: se enviará texto o nota.";
  const currentMode = MODE_LABELS.find((item) => item.value === mode);

  return (
    <form action={sendConversationMessageAction} className="sticky top-4 space-y-4 rounded-3xl border border-white/[0.08] bg-slate-950/70 p-4">
      <input type="hidden" name="conversation_id" value={conversationId} />
      <input type="hidden" name="redirect_to" value={redirectTo} />
      <input type="hidden" name="kind" value={composer.kind} />
      <input type="hidden" name="body" value={composer.body} />
      <input type="hidden" name="whatsapp_payload" value={composer.whatsappPayload ? JSON.stringify(composer.whatsappPayload) : ""} />

      <div>
        <div className="eyebrow">Composer visual de WhatsApp</div>
        <div className="mt-1 text-lg font-semibold text-white">Responder con payload first-class, no solo texto</div>
        <p className="mt-2 text-sm leading-6 text-slate-300">Elige el tipo de salida y el composer arma el payload estructurado para media, templates, botones, listas, flows, productos, catálogo o mark-as-read.</p>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {MODE_LABELS.map((item) => {
          const active = item.value === mode;
          return (
            <button
              key={item.value}
              type="button"
              className={active ? "primary-btn justify-start text-left" : "secondary-btn justify-start text-left"}
              onClick={() => setMode(item.value)}
            >
              <span className="flex flex-col items-start">
                <span>{item.label}</span>
                <span className="text-[11px] uppercase tracking-[0.16em] opacity-80">{item.hint}</span>
              </span>
            </button>
          );
        })}
      </div>

      <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-3 text-xs text-slate-300">
        <div className="flex flex-wrap gap-2">
          <span className="mono-pill">Modo activo: {currentMode?.label}</span>
          <span className="mono-pill">Canal: WhatsApp</span>
          <span className="mono-pill">Payload: {composer.whatsappPayload ? "estructurado" : composer.kind === "note" ? "nota interna" : "texto plano"}</span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Quick replies</div>
        <div className="flex flex-wrap gap-2">
          {QUICK_REPLIES.map((item) => (
            <button key={item} type="button" className="secondary-btn" onClick={() => setBody(item)}>{item.slice(0, 28)}…</button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Snippets operativos</div>
        <div className="flex flex-wrap gap-2">
          {SNIPPETS.map((item) => (
            <button key={item.label} type="button" className="secondary-btn" onClick={() => setBody((value) => value ? `${value}\n\n${item.value}` : item.value)}>{item.label}</button>
          ))}
        </div>
      </div>

      {(mode === "text" || mode === "note") ? (
        <label className="field-label">
          {mode === "note" ? "Nota interna" : "Mensaje"}
          <textarea value={body} onChange={(event) => setBody(event.currentTarget.value)} className="field-input min-h-[180px] w-full" placeholder={mode === "note" ? "Escribe una nota para el equipo" : "Escribe una respuesta clara para el cliente"} />
        </label>
      ) : null}

      {["image", "audio", "document", "video"].includes(mode) ? (
        <div className="grid gap-3 md:grid-cols-2">
          <label className="field-label">Origen del media
            <select className="field-input" value={mediaSourceType} onChange={(event) => setMediaSourceType(event.currentTarget.value as "link" | "id") }>
              <option value="link">Link</option>
              <option value="id">Media ID</option>
            </select>
          </label>
          <label className="field-label">{mediaSourceType === "link" ? "URL del media" : "Media ID"}
            <input className="field-input" value={mediaRef} onChange={(event) => setMediaRef(event.currentTarget.value)} placeholder={mediaSourceType === "link" ? "https://..." : "media-123"} />
          </label>
          <label className="field-label md:col-span-2">Caption / resumen
            <textarea className="field-input min-h-[110px]" value={mediaCaption} onChange={(event) => setMediaCaption(event.currentTarget.value)} placeholder="Texto visible o resumen del adjunto" />
          </label>
          {mode === "document" ? (
            <label className="field-label md:col-span-2">Nombre de archivo
              <input className="field-input" value={mediaFilename} onChange={(event) => setMediaFilename(event.currentTarget.value)} placeholder="cotizacion.pdf" />
            </label>
          ) : null}
        </div>
      ) : null}

      {mode === "template" ? (
        <div className="grid gap-3 md:grid-cols-2">
          <label className="field-label">Nombre del template
            <input className="field-input" value={templateName} onChange={(event) => setTemplateName(event.currentTarget.value)} placeholder="appointment_reminder" />
          </label>
          <label className="field-label">Language code
            <input className="field-input" value={templateLanguageCode} onChange={(event) => setTemplateLanguageCode(event.currentTarget.value)} placeholder="es_MX" />
          </label>
          <label className="field-label md:col-span-2">Parámetros body, uno por línea
            <textarea className="field-input min-h-[120px]" value={templateBodyParams} onChange={(event) => setTemplateBodyParams(event.currentTarget.value)} placeholder={"Mateo\nViernes 5:30 pm\nSucursal Reforma"} />
          </label>
          <label className="field-label md:col-span-2">Resumen visible en el hilo
            <input className="field-input" value={body} onChange={(event) => setBody(event.currentTarget.value)} placeholder="Opcional; si lo dejas vacío el sistema resume con el nombre del template" />
          </label>
        </div>
      ) : null}

      {mode === "interactive_button" ? (
        <div className="space-y-3">
          <label className="field-label">Texto principal
            <textarea className="field-input min-h-[110px]" value={interactiveBody} onChange={(event) => setInteractiveBody(event.currentTarget.value)} placeholder="¿Qué te gustaría hacer ahora?" />
          </label>
          <label className="field-label">Footer
            <input className="field-input" value={interactiveFooter} onChange={(event) => setInteractiveFooter(event.currentTarget.value)} placeholder="Opcional" />
          </label>
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Acciones rápidas disponibles</div>
            <div className="flex gap-2">
              {buttons.length > 1 ? <button type="button" className="secondary-btn" onClick={() => setButtons((value) => value.slice(0, -1))}>Quitar botón</button> : null}
              {buttons.length < MAX_BUTTONS ? <button type="button" className="secondary-btn" onClick={() => setButtons((value) => [...value, { id: `boton_${value.length + 1}`, title: `Opción ${value.length + 1}` }])}>Agregar botón</button> : null}
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {buttons.map((button, index) => (
              <div key={`button-${index}`} className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-3">
                <div className="mb-2 flex items-center justify-between gap-3 text-xs uppercase tracking-[0.16em] text-slate-500"><span>Botón {index + 1}</span><span className="mono-pill">reply</span></div>
                <label className="field-label">ID
                  <input className="field-input" value={button.id} onChange={(event) => setButtons((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, id: event.currentTarget.value } : item))} placeholder={`boton_${index + 1}`} />
                </label>
                <label className="field-label">Título
                  <input className="field-input" value={button.title} onChange={(event) => setButtons((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, title: event.currentTarget.value } : item))} placeholder="Texto visible" />
                </label>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {mode === "interactive_list" ? (
        <div className="space-y-3">
          <label className="field-label">Texto principal
            <textarea className="field-input min-h-[110px]" value={interactiveBody} onChange={(event) => setInteractiveBody(event.currentTarget.value)} placeholder="Elige una opción" />
          </label>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="field-label">Etiqueta del botón
              <input className="field-input" value={listButtonLabel} onChange={(event) => setListButtonLabel(event.currentTarget.value)} placeholder="Ver opciones" />
            </label>
            <label className="field-label">Footer
              <input className="field-input" value={interactiveFooter} onChange={(event) => setInteractiveFooter(event.currentTarget.value)} placeholder="Opcional" />
            </label>
          </div>
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Filas de lista</div>
            <div className="flex gap-2">
              {listRows.length > 1 ? <button type="button" className="secondary-btn" onClick={() => setListRows((value) => value.slice(0, -1))}>Quitar fila</button> : null}
              <button type="button" className="secondary-btn" onClick={() => setListRows((value) => [...value, { section: "Opciones", id: `opcion_${value.length + 1}`, title: `Nueva opción ${value.length + 1}`, description: "" }])}>Agregar fila</button>
            </div>
          </div>
          <div className="space-y-3">
            {listRows.map((row, index) => (
              <div key={`row-${index}`} className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-3">
                <div className="mb-2 flex items-center justify-between gap-3 text-xs uppercase tracking-[0.16em] text-slate-500"><span>Fila {index + 1}</span><span className="mono-pill">list_reply</span></div>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="field-label">Sección
                    <input className="field-input" value={row.section} onChange={(event) => setListRows((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, section: event.currentTarget.value } : item))} placeholder="Opciones" />
                  </label>
                  <label className="field-label">ID
                    <input className="field-input" value={row.id} onChange={(event) => setListRows((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, id: event.currentTarget.value } : item))} placeholder={`row_${index + 1}`} />
                  </label>
                  <label className="field-label">Título
                    <input className="field-input" value={row.title} onChange={(event) => setListRows((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, title: event.currentTarget.value } : item))} placeholder="Texto visible" />
                  </label>
                  <label className="field-label">Descripción
                    <input className="field-input" value={row.description} onChange={(event) => setListRows((value) => value.map((item, itemIndex) => itemIndex === index ? { ...item, description: event.currentTarget.value } : item))} placeholder="Opcional" />
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {mode === "flow_entrypoint" ? (
        <div className="grid gap-3 md:grid-cols-2">
          <label className="field-label">Flow ID
            <input className="field-input" value={flowId} onChange={(event) => setFlowId(event.currentTarget.value)} placeholder="flow-123" />
          </label>
          <label className="field-label">Flow token
            <input className="field-input" value={flowToken} onChange={(event) => setFlowToken(event.currentTarget.value)} placeholder="token opcional" />
          </label>
          <label className="field-label">CTA
            <input className="field-input" value={flowCta} onChange={(event) => setFlowCta(event.currentTarget.value)} placeholder="Abrir flujo" />
          </label>
          <label className="field-label">Footer
            <input className="field-input" value={flowFooter} onChange={(event) => setFlowFooter(event.currentTarget.value)} placeholder="Opcional" />
          </label>
          <label className="field-label md:col-span-2">Texto principal
            <textarea className="field-input min-h-[110px]" value={flowBody} onChange={(event) => setFlowBody(event.currentTarget.value)} placeholder="Completa tu pre-registro" />
          </label>
        </div>
      ) : null}

      {mode === "product" ? (
        <div className="grid gap-3 md:grid-cols-2">
          <label className="field-label">Catalog ID
            <input className="field-input" value={productCatalogId} onChange={(event) => setProductCatalogId(event.currentTarget.value)} placeholder="cat-123" />
          </label>
          <label className="field-label">Product retailer ID
            <input className="field-input" value={productRetailerId} onChange={(event) => setProductRetailerId(event.currentTarget.value)} placeholder="sku-123" />
          </label>
          <label className="field-label md:col-span-2">Texto principal
            <textarea className="field-input min-h-[110px]" value={productBody} onChange={(event) => setProductBody(event.currentTarget.value)} placeholder="Te comparto este producto." />
          </label>
          <label className="field-label md:col-span-2">Footer
            <input className="field-input" value={productFooter} onChange={(event) => setProductFooter(event.currentTarget.value)} placeholder="Opcional" />
          </label>
        </div>
      ) : null}

      {mode === "catalog" ? (
        <div className="grid gap-3 md:grid-cols-2">
          <label className="field-label">Catalog ID
            <input className="field-input" value={catalogId} onChange={(event) => setCatalogId(event.currentTarget.value)} placeholder="cat-123" />
          </label>
          <label className="field-label">Título de sección
            <input className="field-input" value={catalogSectionTitle} onChange={(event) => setCatalogSectionTitle(event.currentTarget.value)} placeholder="Destacados" />
          </label>
          <label className="field-label md:col-span-2">Texto principal
            <textarea className="field-input min-h-[110px]" value={catalogBody} onChange={(event) => setCatalogBody(event.currentTarget.value)} placeholder="Estos son los productos disponibles" />
          </label>
          <label className="field-label md:col-span-2">SKUs, uno por línea
            <textarea className="field-input min-h-[120px]" value={catalogProducts} onChange={(event) => setCatalogProducts(event.currentTarget.value)} placeholder={"sku-1\nsku-2\nsku-3"} />
          </label>
        </div>
      ) : null}

      {mode === "mark_as_read" ? (
        <label className="field-label">Message ID a marcar como leído
          <input className="field-input" value={markAsReadTarget} onChange={(event) => setMarkAsReadTarget(event.currentTarget.value)} placeholder="wamid.HBg..." />
        </label>
      ) : null}

      <div className="rounded-3xl border border-white/[0.08] bg-white/[0.03] p-3">
        <div className="mb-2 text-xs uppercase tracking-[0.16em] text-slate-500">Preview del payload</div>
        <pre className="max-h-[320px] overflow-auto whitespace-pre-wrap text-xs leading-6 text-slate-200">{previewJson}</pre>
      </div>

      {composer.errors.length ? (
        <div className="rounded-3xl border border-amber-400/20 bg-amber-400/10 p-3 text-sm text-amber-100">
          <div className="mb-2 font-semibold">Antes de enviar, corrige esto:</div>
          <ul className="space-y-1">
            {composer.errors.map((error) => <li key={error}>• {error}</li>)}
          </ul>
        </div>
      ) : null}

      <button className="primary-btn w-full" type="submit" disabled={composer.errors.length > 0}>Enviar por WhatsApp</button>
      <div className="text-xs text-slate-400">Tip: este composer ya manda payload estructurado first-class. Lo que ves en el preview es lo que entra al backend y sale al worker.</div>
    </form>
  );
}
