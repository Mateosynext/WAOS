from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

class AutomationRuleRequest(BaseModel):
    organization_id: str
    bot_id: str
    rule_type: Literal["no_response", "post_quote", "no_show", "reactivation"]
    name: str
    status: Literal["active", "paused"] = "active"
    delay_minutes: int = 120
    max_attempts: int = 2
    message_template: str
