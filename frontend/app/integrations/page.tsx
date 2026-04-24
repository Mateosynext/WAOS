import { IntegrationsShell } from "@/features/integrations/components/IntegrationsShell";
import { getIntegrationsPageModel, type IntegrationsSearchParams } from "@/features/integrations/server/getIntegrationsPageModel";

export default async function IntegrationsPage({ searchParams }: { searchParams?: Promise<IntegrationsSearchParams> }) {
  const model = await getIntegrationsPageModel((await searchParams) || {});
  return <IntegrationsShell model={model} />;
}
