"use server";
import { loginAction as loginActionImpl, logoutAction as logoutActionImpl } from "./actions/auth";
import { switchOrganizationAction as switchOrganizationActionImpl, switchBotAction as switchBotActionImpl } from "./actions/selection";
import { sendConversationMessageAction as sendConversationMessageActionImpl, takeoverConversationAction as takeoverConversationActionImpl, reactivateConversationAction as reactivateConversationActionImpl } from "./actions/conversations";
import { testIntegrationAction as testIntegrationActionImpl, syncIntegrationAction as syncIntegrationActionImpl, saveWhatsAppIntegrationAction as saveWhatsAppIntegrationActionImpl, saveGoogleCalendarIntegrationAction as saveGoogleCalendarIntegrationActionImpl, saveStripeIntegrationAction as saveStripeIntegrationActionImpl, startGoogleOAuthAction as startGoogleOAuthActionImpl, refreshPaymentStatusAction as refreshPaymentStatusActionImpl } from "./actions/integrations";
import { createBotAction as createBotActionImpl, applyBotVerticalAction as applyBotVerticalActionImpl, pauseBotAction as pauseBotActionImpl, resumeBotAction as resumeBotActionImpl, publishBotAction as publishBotActionImpl } from "./actions/bots";
import { requestReleaseAction as requestReleaseActionImpl, approveReleaseAction as approveReleaseActionImpl, publishReleaseAction as publishReleaseActionImpl } from "./actions/releases";
import { createSecretAction as createSecretActionImpl, rotateSecretAction as rotateSecretActionImpl } from "./actions/secrets";
import { generateExecutiveReportAction as generateExecutiveReportActionImpl } from "./actions/reports";
import { requeueDeadLetterAction as requeueDeadLetterActionImpl } from "./actions/operations";
import { updateOrganizationVerticalAction as updateOrganizationVerticalActionImpl } from "./actions/organizations";
import { updateTalentPolicyAction as updateTalentPolicyActionImpl, createTalentVacancyAction as createTalentVacancyActionImpl, confirmTalentCandidateAction as confirmTalentCandidateActionImpl } from "./actions/talent";
export async function loginAction(...args: Parameters<typeof loginActionImpl>) { return loginActionImpl(...args); }
export async function logoutAction(...args: Parameters<typeof logoutActionImpl>) { return logoutActionImpl(...args); }
export async function switchOrganizationAction(...args: Parameters<typeof switchOrganizationActionImpl>) { return switchOrganizationActionImpl(...args); }
export async function switchBotAction(...args: Parameters<typeof switchBotActionImpl>) { return switchBotActionImpl(...args); }
export async function sendConversationMessageAction(...args: Parameters<typeof sendConversationMessageActionImpl>) { return sendConversationMessageActionImpl(...args); }
export async function takeoverConversationAction(...args: Parameters<typeof takeoverConversationActionImpl>) { return takeoverConversationActionImpl(...args); }
export async function reactivateConversationAction(...args: Parameters<typeof reactivateConversationActionImpl>) { return reactivateConversationActionImpl(...args); }
export async function testIntegrationAction(...args: Parameters<typeof testIntegrationActionImpl>) { return testIntegrationActionImpl(...args); }
export async function syncIntegrationAction(...args: Parameters<typeof syncIntegrationActionImpl>) { return syncIntegrationActionImpl(...args); }
export async function saveWhatsAppIntegrationAction(...args: Parameters<typeof saveWhatsAppIntegrationActionImpl>) { return saveWhatsAppIntegrationActionImpl(...args); }
export async function saveGoogleCalendarIntegrationAction(...args: Parameters<typeof saveGoogleCalendarIntegrationActionImpl>) { return saveGoogleCalendarIntegrationActionImpl(...args); }
export async function startGoogleOAuthAction(...args: Parameters<typeof startGoogleOAuthActionImpl>) { return startGoogleOAuthActionImpl(...args); }
export async function saveStripeIntegrationAction(...args: Parameters<typeof saveStripeIntegrationActionImpl>) { return saveStripeIntegrationActionImpl(...args); }
export async function refreshPaymentStatusAction(...args: Parameters<typeof refreshPaymentStatusActionImpl>) { return refreshPaymentStatusActionImpl(...args); }
export async function createBotAction(...args: Parameters<typeof createBotActionImpl>) { return createBotActionImpl(...args); }
export async function applyBotVerticalAction(...args: Parameters<typeof applyBotVerticalActionImpl>) { return applyBotVerticalActionImpl(...args); }
export async function pauseBotAction(...args: Parameters<typeof pauseBotActionImpl>) { return pauseBotActionImpl(...args); }
export async function resumeBotAction(...args: Parameters<typeof resumeBotActionImpl>) { return resumeBotActionImpl(...args); }
export async function publishBotAction(...args: Parameters<typeof publishBotActionImpl>) { return publishBotActionImpl(...args); }
export async function requestReleaseAction(...args: Parameters<typeof requestReleaseActionImpl>) { return requestReleaseActionImpl(...args); }
export async function approveReleaseAction(...args: Parameters<typeof approveReleaseActionImpl>) { return approveReleaseActionImpl(...args); }
export async function publishReleaseAction(...args: Parameters<typeof publishReleaseActionImpl>) { return publishReleaseActionImpl(...args); }
export async function createSecretAction(...args: Parameters<typeof createSecretActionImpl>) { return createSecretActionImpl(...args); }
export async function rotateSecretAction(...args: Parameters<typeof rotateSecretActionImpl>) { return rotateSecretActionImpl(...args); }
export async function generateExecutiveReportAction(...args: Parameters<typeof generateExecutiveReportActionImpl>) { return generateExecutiveReportActionImpl(...args); }
export async function requeueDeadLetterAction(...args: Parameters<typeof requeueDeadLetterActionImpl>) { return requeueDeadLetterActionImpl(...args); }

export async function updateOrganizationVerticalAction(...args: Parameters<typeof updateOrganizationVerticalActionImpl>) { return updateOrganizationVerticalActionImpl(...args); }

export async function updateTalentPolicyAction(...args: Parameters<typeof updateTalentPolicyActionImpl>) { return updateTalentPolicyActionImpl(...args); }
export async function createTalentVacancyAction(...args: Parameters<typeof createTalentVacancyActionImpl>) { return createTalentVacancyActionImpl(...args); }
export async function confirmTalentCandidateAction(...args: Parameters<typeof confirmTalentCandidateActionImpl>) { return confirmTalentCandidateActionImpl(...args); }
