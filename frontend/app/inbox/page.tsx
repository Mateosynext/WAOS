import { InboxShell } from "@/features/inbox/components/InboxShell";
import { getInboxPageModel, type InboxSearchParams } from "@/features/inbox/server/getInboxPageModel";

export default async function InboxPage({ searchParams }: { searchParams?: Promise<InboxSearchParams> }) {
  const model = await getInboxPageModel((await searchParams) || {});
  return <InboxShell model={model} />;
}
