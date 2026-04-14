from __future__ import annotations
from ..meta_runtime import complete_meta_embedded_signup, start_meta_embedded_signup
class MetaProviderImpl:
    def start_embedded_signup(self, conn, *, organization_id: str, bot_id: str | None = None) -> dict:
        return start_meta_embedded_signup(conn, organization_id=organization_id, bot_id=bot_id)
    def complete_embedded_signup(self, conn, *, state: str, code: str) -> dict:
        return complete_meta_embedded_signup(conn, state=state, code=code)
meta_provider = MetaProviderImpl()
