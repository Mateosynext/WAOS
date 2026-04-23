import { useMemo, useState } from "react";

import { buildComposerPayload } from "./payload";
import type { ButtonDraft, ComposerMode, ListRowDraft } from "./types";

export function useConversationComposerState() {
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

  const composer = useMemo(() => buildComposerPayload(mode, {
    body,
    mediaSourceType,
    mediaRef,
    mediaCaption,
    mediaFilename,
    templateName,
    templateLanguageCode,
    templateBodyParams,
    interactiveBody,
    interactiveFooter,
    buttons,
    listButtonLabel,
    listRows,
    flowId,
    flowToken,
    flowCta,
    flowBody,
    flowFooter,
    productCatalogId,
    productRetailerId,
    productBody,
    productFooter,
    catalogId,
    catalogBody,
    catalogSectionTitle,
    catalogProducts,
    markAsReadTarget,
  }), [
    body, buttons, catalogBody, catalogId, catalogProducts, catalogSectionTitle, flowBody, flowCta, flowFooter, flowId, flowToken,
    interactiveBody, interactiveFooter, listButtonLabel, listRows, markAsReadTarget, mediaCaption, mediaFilename, mediaRef, mediaSourceType, mode,
    productBody, productCatalogId, productFooter, productRetailerId, templateBodyParams, templateLanguageCode, templateName,
  ]);

  return {
    mode, setMode,
    body, setBody,
    mediaSourceType, setMediaSourceType,
    mediaRef, setMediaRef,
    mediaCaption, setMediaCaption,
    mediaFilename, setMediaFilename,
    templateName, setTemplateName,
    templateLanguageCode, setTemplateLanguageCode,
    templateBodyParams, setTemplateBodyParams,
    interactiveBody, setInteractiveBody,
    interactiveFooter, setInteractiveFooter,
    buttons, setButtons,
    listButtonLabel, setListButtonLabel,
    listRows, setListRows,
    flowId, setFlowId,
    flowToken, setFlowToken,
    flowCta, setFlowCta,
    flowBody, setFlowBody,
    flowFooter, setFlowFooter,
    productCatalogId, setProductCatalogId,
    productRetailerId, setProductRetailerId,
    productBody, setProductBody,
    productFooter, setProductFooter,
    catalogId, setCatalogId,
    catalogBody, setCatalogBody,
    catalogSectionTitle, setCatalogSectionTitle,
    catalogProducts, setCatalogProducts,
    markAsReadTarget, setMarkAsReadTarget,
    composer,
  };
}

export type ConversationComposerState = ReturnType<typeof useConversationComposerState>;
