import { getBearerToken } from "../../../route-helpers";
import { getServerApiBase } from "@/app/lib/env";

function sseFailure(message: string, status = 502) {
  const payload = JSON.stringify({ event_type: "workflow.failed", message, upstream_status: status });
  // EventSource does not expose non-2xx response bodies to the browser. Return a
  // default message-channel SSE payload with status 200 so the UI can render the
  // real failure instead of looking like an idle connection.
  return new Response(`retry: 2500\ndata: ${payload}\n\n`, {
    status: 200,
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
