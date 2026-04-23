import type { ButtonDraft, ComposerMode, ComposerResult, ListRowDraft } from "./types";

const MAX_BUTTONS = 3;

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
    current.push({ id: compact(row.id), title: compact(row.title), description: compact(row.description) || undefined });
    grouped.set(section, current);
  });
  return Array.from(grouped.entries()).map(([title, sectionRows]) => ({ title, rows: sectionRows }));
}

export { MAX_BUTTONS };

export function buildComposerPayload(mode: ComposerMode, state: {
  body: string;
  mediaSourceType: "link" | "id";
  mediaRef: string;
  mediaCaption: string;
  mediaFilename: string;
  templateName: string;
  templateLanguageCode: string;
  templateBodyParams: string;
  interactiveBody: string;
  interactiveFooter: string;
  buttons: ButtonDraft[];
  listButtonLabel: string;
  listRows: ListRowDraft[];
  flowId: string;
  flowToken: string;
  flowCta: string;
  flowBody: string;
  flowFooter: string;
  productCatalogId: string;
  productRetailerId: string;
  productBody: string;
  productFooter: string;
  catalogId: string;
  catalogBody: string;
  catalogSectionTitle: string;
  catalogProducts: string;
  markAsReadTarget: string;
}): ComposerResult {
  const errors: string[] = [];
  const { body } = state;
  if (mode === "note") {
    if (!compact(body)) errors.push("La nota interna necesita texto.");
    return { kind: "note", body, errors };
  }
  if (mode === "text") {
    if (!compact(body)) errors.push("El mensaje de texto necesita contenido.");
    return { kind: "text", body, errors };
  }
  if (["image", "audio", "document", "video"].includes(mode)) {
    if (!compact(state.mediaRef)) errors.push("Necesitas un link o media ID.");
    const media: Record<string, string> = { [state.mediaSourceType]: compact(state.mediaRef) };
    if (compact(state.mediaCaption)) media.caption = compact(state.mediaCaption);
    if (mode === "document" && compact(state.mediaFilename)) media.filename = compact(state.mediaFilename);
    return { kind: "text", body: compact(state.mediaCaption) || body, whatsappPayload: { message_type: mode, media }, errors };
  }
  if (mode === "template") {
    if (!compact(state.templateName)) errors.push("El template necesita nombre.");
    const parameters = buildTemplateParameters(state.templateBodyParams);
    return { kind: "text", body, whatsappPayload: { message_type: "template", template: { name: compact(state.templateName), language: { code: compact(state.templateLanguageCode) || "es_MX" }, components: parameters.length ? [{ type: "body", parameters }] : [] } }, errors };
  }
  if (mode === "interactive_button") {
    const activeButtons = state.buttons.map((item) => ({ id: compact(item.id), title: compact(item.title) })).filter((item) => item.id || item.title);
    if (!compact(state.interactiveBody)) errors.push("Los botones necesitan texto principal.");
    if (!activeButtons.length) errors.push("Agrega al menos un botón.");
    if (activeButtons.length > MAX_BUTTONS) errors.push("WhatsApp solo permite hasta 3 botones.");
    if (activeButtons.some((item) => !item.id || !item.title)) errors.push("Cada botón necesita id y título.");
    return { kind: "text", body: state.interactiveBody, whatsappPayload: { message_type: "interactive_button", interactive: { body: { text: compact(state.interactiveBody) }, footer: compact(state.interactiveFooter) ? { text: compact(state.interactiveFooter) } : undefined, buttons: activeButtons } }, errors };
  }
  if (mode === "interactive_list") {
    const activeRows = state.listRows.map((row) => ({ section: compact(row.section), id: compact(row.id), title: compact(row.title), description: compact(row.description) })).filter((row) => row.id || row.title || row.description);
    if (!compact(state.interactiveBody)) errors.push("La lista necesita texto principal.");
    if (!compact(state.listButtonLabel)) errors.push("La lista necesita etiqueta de botón.");
    if (!activeRows.length) errors.push("Agrega al menos una fila a la lista.");
    if (activeRows.some((row) => !row.id || !row.title)) errors.push("Cada fila necesita id y título.");
    return { kind: "text", body: state.interactiveBody, whatsappPayload: { message_type: "interactive_list", interactive: { body: { text: compact(state.interactiveBody) }, footer: compact(state.interactiveFooter) ? { text: compact(state.interactiveFooter) } : undefined, button: compact(state.listButtonLabel), sections: groupListRows(activeRows) } }, errors };
  }
  if (mode === "flow_entrypoint") {
    if (!compact(state.flowId)) errors.push("El flow necesita flow_id.");
    if (!compact(state.flowBody)) errors.push("El flow necesita body visible.");
    return { kind: "text", body: state.flowBody, whatsappPayload: { message_type: "flow_entrypoint", flow: { flow_id: compact(state.flowId), flow_token: compact(state.flowToken) || undefined, flow_cta: compact(state.flowCta) || "Abrir", body: { text: compact(state.flowBody) }, footer: compact(state.flowFooter) ? { text: compact(state.flowFooter) } : undefined } }, errors };
  }
  if (mode === "product") {
    if (!compact(state.productCatalogId)) errors.push("El producto necesita catalog_id.");
    if (!compact(state.productRetailerId)) errors.push("El producto necesita product_retailer_id.");
    return { kind: "text", body: state.productBody, whatsappPayload: { message_type: "product", product: { catalog_id: compact(state.productCatalogId), product_retailer_id: compact(state.productRetailerId), body: { text: compact(state.productBody) }, footer: compact(state.productFooter) ? { text: compact(state.productFooter) } : undefined } }, errors };
  }
  if (mode === "catalog") {
    const productItems = state.catalogProducts.split(/\r?\n/).map((item) => compact(item)).filter(Boolean);
    if (!compact(state.catalogId)) errors.push("El catálogo necesita catalog_id.");
    if (!productItems.length) errors.push("Agrega al menos un SKU al catálogo.");
    return { kind: "text", body: state.catalogBody, whatsappPayload: { message_type: "catalog", catalog: { catalog_id: compact(state.catalogId), body: { text: compact(state.catalogBody) }, sections: [{ title: compact(state.catalogSectionTitle) || "Destacados", product_items: productItems.map((sku) => ({ product_retailer_id: sku })) }] } }, errors };
  }
  if (!compact(state.markAsReadTarget)) errors.push("Necesitas el message_id a marcar como leído.");
  return { kind: "text", body: "", whatsappPayload: { message_type: "mark_as_read", target_message_id: compact(state.markAsReadTarget) }, errors };
}
