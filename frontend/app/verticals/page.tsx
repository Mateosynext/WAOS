import { VerticalsShell } from "@/features/vertical-selection/components/VerticalsShell";
import { getVerticalsPageModel, type VerticalsSearchParams } from "@/features/vertical-selection/server/getVerticalsPageModel";

export default async function VerticalsPage({ searchParams }: { searchParams?: Promise<VerticalsSearchParams> }) {
  const model = await getVerticalsPageModel((await searchParams) || {});
  return <VerticalsShell model={model} />;
}
