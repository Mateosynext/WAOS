import { getBearerToken } from "../../../route-helpers";
import { getServerApiBase } from "@/app/lib/env";

export async function GET(request: Request, { params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const base = getServerApiBase();
  if (!base) return new Response("event: workflow.failed\ndata: {\"event_type\":\"workflow.failed\",\"message\":\"missing api base\"}\n\n", { status: 500, headers: { "Content-Type": "text/event-stream" } });
  const token = await getBearerToken();
  const lastEventId = request.headers.get("last-event-id");
  try {
    const upstream = await fetch(`${base}/api/v1/ai/workflows/${encodeURIComponent(runId)}/events`, {
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(lastEventId ? { "Last-Event-ID": lastEventId } : {}) },
      cache: "no-store",
    });
    if (!upstream.ok) {
      const text = await upstream.text();
      return new Response(`event: workflow.failed\ndata: ${JSON.stringify({ event_type: "workflow.failed", message: text || "upstream SSE failed" })}\n\n`, { status: upstream.status, headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform" } });
    }
    return new Response(upstream.body || new ReadableStream(), { status: upstream.status, headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no" } });
  } catch (error) {
    const message = error instanceof Error ? error.message : "backend SSE unreachable";
    return new Response(`event: workflow.failed\ndata: ${JSON.stringify({ event_type: "workflow.failed", message })}\n\n`, { status: 502, headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform" } });
  }
}
