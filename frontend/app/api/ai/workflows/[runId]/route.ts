import { proxyJson } from "../../route-helpers";
export async function GET(request: Request, { params }: { params: Promise<{ runId: string }> }) { const { runId } = await params; return proxyJson(request, `/api/v1/ai/workflows/${encodeURIComponent(runId)}`, "GET"); }
