import { getBearerToken } from "../../../route-helpers";
import { getCurrentBotId, getCurrentOrganizationId } from "@/app/lib/session";
import { getServerApiBase } from "@/app/lib/env";

function sseFailure(message: string, status = 502) {
  const payload = JSON.stringify({ event_type: "workflow.stream_error", message, upstream_status: status });
  return new Response(`retry: 2500
data: ${payload}

`, {
    status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "X-Accel-Buffering": "no",
      "X-WAOS-Stream-Error": "true",
      "X-WAOS-Upstream-Status": String(status),
    },
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
  const requestId = request.headers.get("x-request-id") || `web-sse-${crypto.randomUUID()}`;
  const correlationId = request.headers.get("x-correlation-id") || requestId;
  const [organizationId, botId] = await Promise.all([getCurrentOrganizationId(), getCurrentBotId()]);
  try {
    const upstream = await fetch(upstreamUrl.toString(), {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(lastEventId ? { "Last-Event-ID": lastEventId } : {}),
        "X-Request-Id": requestId,
        "X-Correlation-Id": correlationId,
        "X-WAOS-Frontend-Proxy": "ai-workflows-events",
        ...(organizationId ? { "X-WAOS-Org-Id": organizationId, "X-Organization-Id": organizationId } : {}),
        ...(botId ? { "X-WAOS-Bot-Id": botId, "X-Bot-Id": botId } : {}),
      },
      cache: "no-store",
      signal: request.signal,
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
        "X-Request-Id": upstream.headers.get("x-request-id") || requestId,
        "X-Correlation-Id": upstream.headers.get("x-correlation-id") || correlationId,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "backend SSE unreachable";
    return sseFailure(message, 502);
  }
}
