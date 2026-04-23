import { redirect } from "next/navigation";
export default async function BotStudioRedirectPage({ params }: { params: Promise<{ botId: string }> }) { const { botId } = await params; redirect(`/bot-studio/reconfigure/select?bot=${encodeURIComponent(botId)}`); }
