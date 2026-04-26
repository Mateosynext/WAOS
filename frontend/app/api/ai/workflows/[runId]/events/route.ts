import { getBearerToken } from "../../../route-helpers";
import { getServerApiBase } from "@/app/lib/env";

function sseFailure(message: string, status = 502) {
  return new Response(`event: workflow.failed\ndata: ${JSON.stringify({ event_type: "workflow.failed", message })}\n\n`, {
    status,
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no" },
  });
}

export async function GET(request: Request, { params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const base = getServerApiBase();
  if (!base) return sseFailure("missing api base", 500);
  const token = await getBearerToken();
  const url = new URL(request.url);
  const lastEventId = request.headers.get("last-event-id") || url.searchParams.get("last_event_id");
  const upstreamUrl = new URL(`${base}/api/v1/ai/workflows/${encodeURIComponent(runId)}/events`);
  if (lastEventId) upstreamUrl.searchParams.set("last_event_id", lastEventId);
  try {
    const upstream = await fetch(upstreamUrl.toString(), {
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(lastEventId ? { "Last-Event-ID": lastEventId } : {}) },
      cache: "no-store",
    });
    if (!upstream.ok) {
      const text = await upstream.text();
      return sseFailure(text || "upstream SSE failed", upstream.status);
    }
    return new Response(upstream.body || new ReadableStream(), {
      status: upstream.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "backend SSE unreachable";
    return sseFailure(message, 502);
  }
}
