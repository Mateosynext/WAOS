import Link from "next/link";
import { Shell } from "@/app/components/layout/shell";
import type { VerticalsPageModel } from "@/features/vertical-selection/server/getVerticalsPageModel";
import { SubverticalPanel } from "./SubverticalPanel";
import { TransactionalMotorPanel } from "./TransactionalMotorPanel";
import { VerticalCatalog, VerticalCatalogEmpty } from "./VerticalCatalog";
import { VerticalProfile } from "./VerticalProfile";
import { VerticalReadiness } from "./VerticalReadiness";

export function VerticalsShell({ model }: { model: VerticalsPageModel }) {
  if (!model.profile) return <VerticalCatalogEmpty model={model} />;

  return (
    <Shell title="Portafolio vertical WAOS" subtitle="Una capa de producto y GTM para vender WAOS como sistema operativo conversacional por vertical, no como bot horizontal. Cada vertical baja a buyer, lanzamiento, objetos nativos, pipeline, playbook, automatizaciones y KPIs." action={<Link href="/onboarding" className="primary-btn">Ir a onboarding</Link>}>
      <VerticalCatalog model={model} />
      <VerticalProfile model={model} />
      <SubverticalPanel model={model} />
      <VerticalReadiness model={model} />
      <TransactionalMotorPanel model={model} />
    </Shell>
  );
}
