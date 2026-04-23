import { getClientOperationsData } from "../../../lib/data/client-operations";

export type ClientOperationsPayload = Awaited<ReturnType<typeof getClientOperationsData>>;
