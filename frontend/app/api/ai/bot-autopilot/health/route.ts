import { proxyJson } from "../../route-helpers";
export async function GET(request: Request) { return proxyJson(request, "/api/v1/ai/bot-autopilot/health", "GET"); }
