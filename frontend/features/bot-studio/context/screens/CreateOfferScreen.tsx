"use client";

import { FieldGroup, TextAreaField } from "@/features/bot-studio/ui/flowUi";
import type { CreateOfferActions, CreateOfferViewModel } from "../createScreenTypes";

export function CreateOfferScreen({ viewModel: state, actions: handlers }: { viewModel: CreateOfferViewModel; actions: CreateOfferActions }) {
  return (
    <FieldGroup testId="create-offer-step" title="Captura la oferta comercial" description="CTA, servicios y pricing viven aislados aquí.">
      <TextAreaField testId="services-textarea" label="Servicios" value={state.servicesText} onChange={handlers.setServicesText} />
      <TextAreaField testId="featured-offers-textarea" label="Ofertas destacadas" value={state.featuredOffersText} onChange={handlers.setFeaturedOffersText} />
      <TextAreaField testId="primary-ctas-textarea" label="CTA principales" value={state.primaryCtasText} onChange={handlers.setPrimaryCtasText} />
      <TextAreaField testId="pricing-notes-textarea" label="Notas de pricing" value={state.pricingNotesText} onChange={handlers.setPricingNotesText} />
    </FieldGroup>
  );
}
