from __future__ import annotations
from ..integrations_runtime import build_google_oauth_url, exchange_google_oauth_code, get_google_calendar_availability, list_google_calendars, sync_google_calendar, test_google_calendar_connection
class GoogleCalendarProvider:
    def build_oauth_url(self, conn, integration: dict) -> dict:
        return build_google_oauth_url(conn, integration)
    def exchange_code(self, conn, *, state: str, code: str) -> dict:
        return exchange_google_oauth_code(conn, state=state, code=code)
    def availability(self, conn, integration: dict, *, date: str | None = None) -> dict:
        return get_google_calendar_availability(conn, integration, date=date)
    def sync(self, conn, integration: dict) -> dict:
        return sync_google_calendar(conn, integration)
    def test_connection(self, conn, integration: dict) -> dict:
        return test_google_calendar_connection(conn, integration)
    def list_calendars(self, conn, integration: dict) -> list[dict]:
        return list_google_calendars(conn, integration)
google_calendar_provider = GoogleCalendarProvider()
