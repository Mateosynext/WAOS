export type WaosPublicEvent = {
  organization_id: string;
  bot_id?: string;
  conversation_id?: string;
  contact_id?: string;
  channel: "whatsapp" | "telegram" | "instagram_dm" | "sms" | "email" | "webchat";
  direction?: "inbound" | "outbound";
  event_type?: string;
  body?: string;
  external_thread_id?: string;
  external_user_id?: string;
  identities?: Array<{ type: string; value: string; confidence?: number }>;
  metadata?: Record<string, unknown>;
};

export type WaosSdkRequestOptions = {
  method?: "GET" | "POST";
  body?: unknown;
  headers?: Record<string, string>;
};

export class WaosPublicSDK {
  constructor(private readonly baseUrl: string, private readonly apiKey: string) {}

  private async request(path: string, options: WaosSdkRequestOptions = {}) {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: options.method ?? "GET",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "X-WAOS-Public-Key": this.apiKey,
        ...(options.headers ?? {}),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
    if (!response.ok) throw new Error(`WAOS SDK error ${response.status} on ${path}`);
    return response.json();
  }

  async manifest() {
    return this.request(`/api/public/sdk/manifest`, { method: "GET", headers: {} });
  }

  async sendChannelEvent(payload: WaosPublicEvent) {
    return this.request(`/api/public/v1/channels/events`, { method: "POST", body: payload });
  }

  async unifiedInboxOverview(params: { organization_id: string; bot_id?: string }) {
    const query = new URLSearchParams({ organization_id: params.organization_id, ...(params.bot_id ? { bot_id: params.bot_id } : {}) });
    return this.request(`/api/v1/unified-inbox/overview?${query.toString()}`, { method: "GET" });
  }

  async autoscalingRecommendation(params: { organization_id?: string }) {
    const query = new URLSearchParams(params.organization_id ? { organization_id: params.organization_id } : {});
    return this.request(`/api/v1/runtime/autoscaling${query.toString() ? `?${query.toString()}` : ""}`, { method: "GET" });
  }
}
