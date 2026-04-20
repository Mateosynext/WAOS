import { NextResponse } from "next/server";
import { getVerticalCatalog } from "../../../../lib/waos";

export async function GET() {
  const verticals = await getVerticalCatalog(false);
  return NextResponse.json(verticals, {
    headers: { "Cache-Control": "no-store" },
  });
}
