import type { ConversationComposerState } from "../useConversationComposerState";

export function ConversationComposerCommerceModePanel({ state }: { state: ConversationComposerState }) {
  const {
    mode,
    productCatalogId,
    setProductCatalogId,
    productRetailerId,
    setProductRetailerId,
    productBody,
    setProductBody,
    productFooter,
    setProductFooter,
    catalogId,
    setCatalogId,
    catalogBody,
    setCatalogBody,
    catalogSectionTitle,
    setCatalogSectionTitle,
    catalogProducts,
    setCatalogProducts,
  } = state;

  if (mode === "product") {
    return (
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
    );
  }

  if (mode === "catalog") {
    return (
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
    );
  }

  return null;
}
