import type { CommercialDocumentContract, CommercialDocumentsOverviewContract, CRMPipelineSummaryContract, CRMLeadContract, CatalogProductContract, CatalogServiceContract, CommerceInsightsContract, MediaAssetContract, OrganizationBrandingContract, PaymentContract, PromotionContract } from "../contracts/commerce";
import { normalizeCommercialDocument, normalizeCommercialDocumentsOverview, normalizeCRMPipelineSummary, normalizeCRMLead, normalizeCatalogProduct, normalizeCatalogService, normalizeCommerceInsights, normalizeMediaAsset, normalizeOrganizationBranding, normalizePayment, normalizePromotion } from "../contracts/commerce";
import { apiFetchOrDefault } from "../api";
import { fetchArray, fetchRecord, orgQuery } from "./shared";

export type CommerceInsightsResponse = CommerceInsightsContract;

export async function getPayments(): Promise<PaymentContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/sales/payments?${query}`, [], normalizePayment);
}

export async function getCRMLeads(): Promise<CRMLeadContract[]> {
  const query = await orgQuery();
  return fetchArray(`/api/v1/crm/leads?${query}`, [], normalizeCRMLead);
}

export async function getSellerMode(conversationId: string) {
  return apiFetchOrDefault<Record<string, unknown>>(`/api/v1/sales/mode/${conversationId}`, {});
}

export async function getPlaybooks() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/playbooks?${query}`, []);
}

export async function getCRMPipelineSummary(botId?: string): Promise<CRMPipelineSummaryContract> {
  const query = await orgQuery();
  const suffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchRecord(`/api/v1/crm/pipeline-summary?${query}${suffix}`, { total_leads: 0, weighted_amount: 0, stages: [], lost_reasons: [], recent_stage_changes: [] }, normalizeCRMPipelineSummary);
}

export async function getCatalogCategories() {
  const query = await orgQuery();
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/catalog/categories?${query}`, []);
}

export async function getCatalogProducts(botId?: string): Promise<CatalogProductContract[]> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchArray(`/api/v1/catalog/products?${query}${botSuffix}`, [], normalizeCatalogProduct);
}

export async function getCatalogServices(botId?: string): Promise<CatalogServiceContract[]> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchArray(`/api/v1/catalog/services?${query}${botSuffix}`, [], normalizeCatalogService);
}

export async function getMediaAssets(botId?: string): Promise<MediaAssetContract[]> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchArray(`/api/v1/media/assets?${query}${botSuffix}`, [], normalizeMediaAsset);
}

export async function getPromotions(botId?: string): Promise<PromotionContract[]> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchArray(`/api/v1/promotions?${query}${botSuffix}`, [], normalizePromotion);
}

export async function getPromotionRules(promotionId?: string) {
  const query = await orgQuery();
  const promoSuffix = promotionId ? `&promotion_id=${encodeURIComponent(promotionId)}` : "";
  return apiFetchOrDefault<Array<Record<string, unknown>>>(`/api/v1/promotions/rules?${query}${promoSuffix}`, []);
}

export async function getCommerceInsights(botId?: string): Promise<CommerceInsightsResponse> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchRecord(`/api/v1/commerce/insights?${query}${botSuffix}`, { summary: {}, top_products: [], top_assets: [], top_promotions: [], recommendations: [], alerts: [] }, normalizeCommerceInsights);
}

export async function getCommercialDocuments(botId?: string): Promise<CommercialDocumentContract[]> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchArray(`/api/v1/commercial-documents?${query}${botSuffix}`, [], normalizeCommercialDocument);
}

export async function getCommercialDocumentsOverview(botId?: string): Promise<CommercialDocumentsOverviewContract> {
  const query = await orgQuery();
  const botSuffix = botId ? `&bot_id=${encodeURIComponent(botId)}` : "";
  return fetchRecord(`/api/v1/commercial-documents/overview?${query}${botSuffix}`, { summary: {}, by_status: {}, by_type: {}, amount_by_type: {}, recent: [], recommendations: [] }, normalizeCommercialDocumentsOverview);
}

export async function getOrganizationBranding(): Promise<OrganizationBrandingContract> {
  const query = await orgQuery();
  return fetchRecord(`/api/v1/organization-branding?${query}`, { organization_id: "", business_name: "", primary_color: "#25D366", secondary_color: "#111827" }, normalizeOrganizationBranding);
}
