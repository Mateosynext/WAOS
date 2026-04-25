"use server";

import { redirect } from "next/navigation";
import { getCurrentBotId, getCurrentOrganizationId } from "../lib/session";
import { postJson, readString, runAndRefresh, withActionError } from "./shared";

export async function draftCommercialDocumentAction(formData: FormData) {
  const organizationId = (await getCurrentOrganizationId()) || readString(formData, "organization_id");
  const botId = (await getCurrentBotId()) || readString(formData, "bot_id") || null;
  const redirectTo = readString(formData, "redirect_to") || "/business-hub?tab=documentos";
  const requestText = readString(formData, "request_text");
  const customerName = readString(formData, "customer_name") || null;
  const customerPhone = readString(formData, "customer_phone") || null;
  const documentType = readString(formData, "document_type") || "quote";
  const result = await runAndRefresh(redirectTo, () => postJson("/api/v1/commercial-documents/draft-from-catalog", {
    organization_id: organizationId,
    bot_id: botId,
    document_type: documentType,
    request_text: requestText,
    customer_name: customerName,
    customer_phone: customerPhone,
    auto_generate_pdf: true,
  }));
  if (!result.ok) redirect(withActionError(redirectTo, result.error, "No se pudo crear el documento comercial."));
  redirect(redirectTo);
}

export async function updateCommercialDocumentStatusAction(formData: FormData) {
  const documentId = readString(formData, "document_id");
  const status = readString(formData, "status");
  const redirectTo = readString(formData, "redirect_to") || "/business-hub?tab=documentos";
  const result = await runAndRefresh(redirectTo, () => postJson(`/api/v1/commercial-documents/${encodeURIComponent(documentId)}/status`, { status }));
  if (!result.ok) redirect(withActionError(redirectTo, result.error, "No se pudo actualizar el estado del documento."));
  redirect(redirectTo);
}

export async function convertCommercialDocumentToWorkOrderAction(formData: FormData) {
  const documentId = readString(formData, "document_id");
  const redirectTo = readString(formData, "redirect_to") || "/business-hub?tab=documentos";
  const result = await runAndRefresh(redirectTo, () => postJson(`/api/v1/commercial-documents/${encodeURIComponent(documentId)}/convert-to-work-order`, {}));
  if (!result.ok) redirect(withActionError(redirectTo, result.error, "No se pudo convertir a orden de trabajo."));
  redirect(redirectTo);
}

export async function sendCommercialDocumentAction(formData: FormData) {
  const documentId = readString(formData, "document_id");
  const redirectTo = readString(formData, "redirect_to") || "/business-hub?tab=documentos";
  const messageBody = readString(formData, "message_body") || null;
  const result = await runAndRefresh(redirectTo, () => postJson(`/api/v1/commercial-documents/${encodeURIComponent(documentId)}/send`, {
    message_body: messageBody,
    create_payment: true,
  }));
  if (!result.ok) redirect(withActionError(redirectTo, result.error, "No se pudo enviar el documento por WhatsApp."));
  redirect(redirectTo);
}

export async function acceptCommercialDocumentAction(formData: FormData) {
  const documentId = readString(formData, "document_id");
  const redirectTo = readString(formData, "redirect_to") || "/business-hub?tab=documentos";
  const result = await runAndRefresh(redirectTo, () => postJson(`/api/v1/commercial-documents/${encodeURIComponent(documentId)}/accept`, { metadata: { source: "business_hub" } }));
  if (!result.ok) redirect(withActionError(redirectTo, result.error, "No se pudo aceptar el documento."));
  redirect(redirectTo);
}

export async function createCommercialDocumentPaymentAction(formData: FormData) {
  const documentId = readString(formData, "document_id");
  const redirectTo = readString(formData, "redirect_to") || "/business-hub?tab=documentos";
  const result = await runAndRefresh(redirectTo, () => postJson(`/api/v1/commercial-documents/${encodeURIComponent(documentId)}/payment`, { amount_mode: "deposit" }));
  if (!result.ok) redirect(withActionError(redirectTo, result.error, "No se pudo crear el anticipo."));
  redirect(redirectTo);
}
