"use server";
import { postJson, readString, runAndRefresh } from "./shared";
export async function requeueDeadLetterAction(formData: FormData) { const kind = readString(formData, "kind"); const itemId = readString(formData, "item_id"); const redirectTo = readString(formData, "redirect_to") || "/operations"; await runAndRefresh(redirectTo, () => postJson(`/api/v1/operations/dead-letters/${kind}/${itemId}/requeue`, {})); }
