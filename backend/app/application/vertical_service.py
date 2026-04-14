from __future__ import annotations

from ..domains.bot_behavior import upsert_bot_behavior_settings, upsert_bot_response_template
from ..verticals import build_vertical_bot_setup


class VerticalApplicationService:
    def build_setup(self, *, vertical: str, business_name: str, bot_name: str, tone: str, language: str, timezone: str, primary_objective: str, services: list[str], faqs: list[dict], hours: str, whatsapp_number: str) -> dict:
        return build_vertical_bot_setup(vertical, business_name=business_name, bot_name=bot_name, tone=tone, language=language, timezone=timezone, primary_objective=primary_objective, services=services, faqs=faqs, hours=hours, whatsapp_number=whatsapp_number)

    def apply(self, conn, *, user: dict, organization_id: str, bot_id: str, vertical: str, business_name: str, bot_name: str, tone: str, language: str, timezone: str, primary_objective: str, services: list[str], faqs: list[dict], hours: str, whatsapp_number: str, replace_templates: bool = False) -> dict:
        setup = self.build_setup(vertical=vertical, business_name=business_name, bot_name=bot_name, tone=tone, language=language, timezone=timezone, primary_objective=primary_objective, services=services, faqs=faqs, hours=hours, whatsapp_number=whatsapp_number)
        behavior = setup.get("behavior_settings", {})
        upsert_bot_behavior_settings(conn, organization_id=organization_id, bot_id=bot_id, tone=behavior.get("tone", tone), response_length=behavior.get("response_length", "media"), use_emojis=bool(behavior.get("use_emojis", False)), sales_intensity=behavior.get("sales_intensity", "media"), offer_promotions_when=behavior.get("offer_promotions_when", "when_relevant"), escalate_when=behavior.get("escalate_when", []), insistence_policy=behavior.get("insistence_policy", "respectful"), can_share_price_directly=bool(behavior.get("can_share_price_directly", True)), can_negotiate=bool(behavior.get("can_negotiate", False)), can_mention_stock=bool(behavior.get("can_mention_stock", True)), auto_send_images=bool(behavior.get("auto_send_images", True)), bot_mode=behavior.get("bot_mode", "hybrid"), active_channels=behavior.get("active_channels", ["whatsapp"]), forbidden_topics=behavior.get("forbidden_topics", []), required_phrases=behavior.get("required_phrases", []), fallback_message=behavior.get("fallback_message", "Te ayudo con gusto. Cuéntame un poco mas para orientarte mejor."), actor_user=user)
        if replace_templates:
            conn.execute("DELETE FROM bot_response_templates WHERE organization_id = ? AND bot_id = ?", (organization_id, bot_id))
        for template in setup.get("response_templates", []):
            upsert_bot_response_template(conn, organization_id=organization_id, bot_id=bot_id, template_key=template.get("template_key", "template"), channel="whatsapp", title=template.get("title"), content=template.get("content", ""), variables=template.get("variables", []), is_active=True, actor_user=user)
        return setup


vertical_service = VerticalApplicationService()
