from __future__ import annotations
from ..sso_runtime import build_sso_authorization_url, exchange_sso_code, test_sso_provider_connection
class SSOProviderImpl:
    def build_authorization_url(self, conn, provider: dict) -> dict:
        return build_sso_authorization_url(conn, provider)
    def exchange_code(self, conn, *, state: str, code: str, ip_address: str | None = None, user_agent: str | None = None) -> dict:
        return exchange_sso_code(conn, state=state, code=code, ip_address=ip_address, user_agent=user_agent)
    def test_connection(self, conn, provider: dict) -> dict:
        return test_sso_provider_connection(conn, provider)
sso_provider = SSOProviderImpl()
