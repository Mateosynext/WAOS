"use server";
import { redirect } from "next/navigation";
import { BOT_COOKIE, ORG_COOKIE, cookies, readString, secureCookies } from "./shared";
export async function switchOrganizationAction(formData: FormData) { const organizationId = readString(formData, "organization_id"); const redirectTo = readString(formData, "redirect_to") || "/"; const store = await cookies(); if (organizationId) store.set(ORG_COOKIE, organizationId, { httpOnly: true, sameSite: "lax", secure: secureCookies, path: "/" }); else store.delete(ORG_COOKIE); store.delete(BOT_COOKIE); redirect(redirectTo); }
export async function switchBotAction(formData: FormData) { const botId = readString(formData, "bot_id"); const redirectTo = readString(formData, "redirect_to") || "/bots"; const store = await cookies(); if (botId) store.set(BOT_COOKIE, botId, { httpOnly: true, sameSite: "lax", secure: secureCookies, path: "/" }); else store.delete(BOT_COOKIE); redirect(redirectTo); }
