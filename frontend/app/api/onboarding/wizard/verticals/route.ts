import { wizardRouteResponse } from "../route-helpers";
import { getVerticalCatalog } from "../../../../lib/data/verticals";

export async function GET() {
  return wizardRouteResponse(() => getVerticalCatalog(false), "No se pudo cargar el catálogo vertical del wizard.");
}
