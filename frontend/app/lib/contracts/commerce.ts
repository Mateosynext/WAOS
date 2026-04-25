import {
  asArray,
  asRecord,
  booleanOrNull,
  booleanValue,
  JsonMap,
  nullableNumber,
  numberOrNull,
  numberValue,
  pickString,
  pickTimestamp,
  stringList,
  stringOrNull,
  stringValue,
  unwrapApiEnvelope,
} from "./shared";

export type PaymentContract = {
  id: string;
  reference?: string;
  amount: number;
  currency?: string;
  status?: string;
  provider?: string | null;
  provider_status?: string | null;
  checkout_status?: string | null;
  checkout_url?: string | null;
  appointment_id?: string | null;
  reconciliation_status?: string | null;
  created_at?: string | null;
};

export function normalizePayment(raw: unknown): PaymentContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id || record.reference),
    reference: stringOrNull(record.reference) ?? undefined,
    amount: numberValue(record.amount),
    currency: stringOrNull(record.currency) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    provider: stringOrNull(record.provider),
    provider_status: stringOrNull(record.provider_status),
    checkout_status: stringOrNull(record.checkout_status ?? record.payment_link_status),
    checkout_url: stringOrNull(record.checkout_url ?? record.payment_link_url),
    appointment_id: stringOrNull(record.appointment_id),
    reconciliation_status: stringOrNull(record.reconciliation_status),
    created_at: pickTimestamp(record, "created_at", "paid_at") ?? null,
  };
}

export type CRMLeadContract = {
  id: string;
  contact_name?: string;
  status?: string;
  stage?: string;
  score?: number | null;
};

export function normalizeCRMLead(raw: unknown): CRMLeadContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    contact_name: stringOrNull(record.contact_name ?? record.name) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    stage: stringOrNull(record.stage ?? record.lead_stage) ?? undefined,
    score: nullableNumber(record.score ?? record.lead_score),
  };
}

export type CatalogProductContract = {
  id: string;
  name: string;
  price?: number | null;
  promotional_price?: number | null;
  currency?: string;
  short_description?: string;
  delivery_eta?: string;
  inventory: JsonMap[];
};

export function normalizeCatalogProduct(raw: unknown): CatalogProductContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "title"], "Producto"),
    price: nullableNumber(record.price),
    promotional_price: nullableNumber(record.promotional_price),
    currency: stringOrNull(record.currency) ?? undefined,
    short_description: stringOrNull(record.short_description) ?? undefined,
    delivery_eta: stringOrNull(record.delivery_eta) ?? undefined,
    inventory: asArray(record.inventory).map((item) => asRecord(item)),
  };
}

export type CatalogServiceContract = {
  id: string;
  name: string;
  price?: number | null;
  currency?: string;
  duration_minutes?: number | null;
  branch?: string;
};

export function normalizeCatalogService(raw: unknown): CatalogServiceContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "title"], "Servicio"),
    price: nullableNumber(record.price),
    currency: stringOrNull(record.currency) ?? undefined,
    duration_minutes: nullableNumber(record.duration_minutes),
    branch: stringOrNull(record.branch) ?? undefined,
  };
}

export type MediaAssetContract = {
  id: string;
  name: string;
  file_name?: string;
  label?: string;
  asset_type?: string;
  type?: string;
  status?: string;
  file_url?: string;
  url?: string;
  created_at?: string | null;
};

export function normalizeMediaAsset(raw: unknown): MediaAssetContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "title", "filename", "file_name"], "Asset"),
    file_name: stringOrNull(record.file_name ?? record.filename) ?? undefined,
    label: stringOrNull(record.label) ?? undefined,
    asset_type: stringOrNull(record.asset_type ?? record.type ?? record.kind) ?? undefined,
    type: stringOrNull(record.type ?? record.kind ?? record.asset_type) ?? undefined,
    status: stringOrNull(record.status) ?? undefined,
    file_url: stringOrNull(record.file_url ?? record.url ?? record.asset_url) ?? undefined,
    url: stringOrNull(record.url ?? record.asset_url ?? record.file_url) ?? undefined,
    created_at: pickTimestamp(record, "created_at", "updated_at") ?? null,
  };
}

export type PromotionContract = {
  id: string;
  name: string;
  status?: string;
  cta_label?: string;
  message_short?: string;
  message_long?: string;
  starts_at?: string | null;
  ends_at?: string | null;
};

export function normalizePromotion(raw: unknown): PromotionContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    name: pickString(record, ["name", "title"], "Promoción"),
    status: stringOrNull(record.status) ?? undefined,
    cta_label: stringOrNull(record.cta_label) ?? undefined,
    message_short: stringOrNull(record.message_short ?? record.summary) ?? undefined,
    message_long: stringOrNull(record.message_long ?? record.detail) ?? undefined,
    starts_at: pickTimestamp(record, "starts_at") ?? null,
    ends_at: pickTimestamp(record, "ends_at") ?? null,
  };
}

export type CommerceInsightsContract = {
  summary: JsonMap;
  top_products: JsonMap[];
  top_assets: JsonMap[];
  top_promotions: JsonMap[];
  recommendations: JsonMap[];
  alerts: JsonMap[];
};

export function normalizeCommerceInsights(raw: unknown): CommerceInsightsContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    summary: asRecord(record.summary),
    top_products: asArray(record.top_products).map((item) => asRecord(item)),
    top_assets: asArray(record.top_assets).map((item) => asRecord(item)),
    top_promotions: asArray(record.top_promotions).map((item) => asRecord(item)),
    recommendations: asArray(record.recommendations).map((item) => asRecord(item)),
    alerts: asArray(record.alerts).map((item) => asRecord(item)),
  };
}

export type CRMPipelineSummaryContract = {
  total_leads: number;
  weighted_amount: number;
  stages: Record<string, unknown>[];
  lost_reasons: Record<string, unknown>[];
  recent_stage_changes: Record<string, unknown>[];
};

export function normalizeCRMPipelineSummary(raw: unknown): CRMPipelineSummaryContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    total_leads: numberValue(record.total_leads),
    weighted_amount: numberValue(record.weighted_amount),
    stages: asArray(record.stages).map((item) => asRecord(item)),
    lost_reasons: asArray(record.lost_reasons).map((item) => asRecord(item)),
    recent_stage_changes: asArray(record.recent_stage_changes).map((item) => asRecord(item)),
  };
}

export type CommercialDocumentItemContract = {
  id?: string;
  source_type?: string;
  source_id?: string | null;
  name: string;
  description?: string | null;
  quantity: number;
  unit?: string;
  unit_price: number;
  discount?: number;
  tax?: number;
  total: number;
  metadata?: JsonMap;
};

export type CommercialDocumentContract = {
  id: string;
  organization_id?: string;
  bot_id?: string | null;
  conversation_id?: string | null;
  contact_id?: string | null;
  document_type: string;
  folio: string;
  status: string;
  title: string;
  customer_name?: string | null;
  customer_phone?: string | null;
  customer_email?: string | null;
  customer_address?: string | null;
  summary?: string | null;
  currency: string;
  subtotal: number;
  discount_total: number;
  tax_total: number;
  total: number;
  deposit_required: number;
  balance_due: number;
  valid_until?: string | null;
  pdf_filename?: string | null;
  pdf_generated_at?: string | null;
  public_url?: string | null;
  payment_url?: string | null;
  terms?: string | null;
  missing_questions: string[];
  approval_reasons: string[];
  next_actions: string[];
  metadata: JsonMap;
  created_at?: string | null;
  updated_at?: string | null;
  items: CommercialDocumentItemContract[];
};

export type CommercialDocumentsOverviewContract = {
  summary: JsonMap;
  by_status: JsonMap;
  by_type: JsonMap;
  amount_by_type: JsonMap;
  recent: CommercialDocumentContract[];
  recommendations: string[];
};

export type OrganizationBrandingContract = {
  organization_id: string;
  business_name?: string;
  legal_name?: string | null;
  logo_url?: string | null;
  primary_color?: string;
  secondary_color?: string;
  phone?: string | null;
  whatsapp?: string | null;
  email?: string | null;
  website?: string | null;
  address?: string | null;
  footer_note?: string | null;
  metadata?: JsonMap;
};

export function normalizeCommercialDocumentItem(raw: unknown): CommercialDocumentItemContract {
  const record = asRecord(raw);
  return {
    id: stringOrNull(record.id) ?? undefined,
    source_type: stringOrNull(record.source_type) ?? undefined,
    source_id: stringOrNull(record.source_id),
    name: pickString(record, ["name", "title"], "Concepto"),
    description: stringOrNull(record.description),
    quantity: numberValue(record.quantity, 1),
    unit: stringOrNull(record.unit) ?? undefined,
    unit_price: numberValue(record.unit_price),
    discount: numberValue(record.discount),
    tax: numberValue(record.tax),
    total: numberValue(record.total),
    metadata: asRecord(record.metadata ?? record.metadata_json),
  };
}

export function normalizeCommercialDocument(raw: unknown): CommercialDocumentContract {
  const record = asRecord(raw);
  return {
    id: stringValue(record.id),
    organization_id: stringOrNull(record.organization_id) ?? undefined,
    bot_id: stringOrNull(record.bot_id),
    conversation_id: stringOrNull(record.conversation_id),
    contact_id: stringOrNull(record.contact_id),
    document_type: stringOrNull(record.document_type) ?? "quote",
    folio: stringOrNull(record.folio) ?? "DOC",
    status: stringOrNull(record.status) ?? "draft",
    title: pickString(record, ["title", "name"], "Documento comercial"),
    customer_name: stringOrNull(record.customer_name),
    customer_phone: stringOrNull(record.customer_phone),
    customer_email: stringOrNull(record.customer_email),
    customer_address: stringOrNull(record.customer_address),
    summary: stringOrNull(record.summary),
    currency: stringOrNull(record.currency) ?? "MXN",
    subtotal: numberValue(record.subtotal),
    discount_total: numberValue(record.discount_total),
    tax_total: numberValue(record.tax_total),
    total: numberValue(record.total),
    deposit_required: numberValue(record.deposit_required),
    balance_due: numberValue(record.balance_due),
    valid_until: pickTimestamp(record, "valid_until") ?? null,
    pdf_filename: stringOrNull(record.pdf_filename),
    pdf_generated_at: pickTimestamp(record, "pdf_generated_at") ?? null,
    public_url: stringOrNull(record.public_url),
    payment_url: stringOrNull(record.payment_url),
    terms: stringOrNull(record.terms),
    missing_questions: stringList(record.missing_questions ?? record.missing_questions_json),
    approval_reasons: stringList(record.approval_reasons ?? record.approval_reasons_json),
    next_actions: stringList(record.next_actions ?? record.next_actions_json),
    metadata: asRecord(record.metadata ?? record.metadata_json),
    created_at: pickTimestamp(record, "created_at") ?? null,
    updated_at: pickTimestamp(record, "updated_at") ?? null,
    items: asArray(record.items).map((item) => normalizeCommercialDocumentItem(item)),
  };
}

export function normalizeCommercialDocumentsOverview(raw: unknown): CommercialDocumentsOverviewContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    summary: asRecord(record.summary),
    by_status: asRecord(record.by_status),
    by_type: asRecord(record.by_type),
    amount_by_type: asRecord(record.amount_by_type),
    recent: asArray(record.recent).map((item) => normalizeCommercialDocument(item)),
    recommendations: stringList(record.recommendations),
  };
}

export function normalizeOrganizationBranding(raw: unknown): OrganizationBrandingContract {
  const record = asRecord(unwrapApiEnvelope(raw));
  return {
    organization_id: stringValue(record.organization_id),
    business_name: stringOrNull(record.business_name) ?? undefined,
    legal_name: stringOrNull(record.legal_name),
    logo_url: stringOrNull(record.logo_url),
    primary_color: stringOrNull(record.primary_color) ?? undefined,
    secondary_color: stringOrNull(record.secondary_color) ?? undefined,
    phone: stringOrNull(record.phone),
    whatsapp: stringOrNull(record.whatsapp),
    email: stringOrNull(record.email),
    website: stringOrNull(record.website),
    address: stringOrNull(record.address),
    footer_note: stringOrNull(record.footer_note),
    metadata: asRecord(record.metadata ?? record.metadata_json),
  };
}
