import { proxyJson } from "../route-helpers";
export async function POST(request: Request) { return proxyJson(request, "/api/v1/ai/bot-autopilot", "POST"); }
