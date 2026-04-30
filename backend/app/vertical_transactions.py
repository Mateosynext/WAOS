from __future__ import annotations

from typing import Any

def ensure_vertical_transaction_schema(conn) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS vertical_transactions (
        id TEXT PRIMARY KEY,
        organization_id TEXT,
        bot_id TEXT,
        account_id TEXT,
        provider TEXT,
        provider_status TEXT,
        amount REAL NOT NULL DEFAULT 0,
        currency TEXT NOT NULL DEFAULT 'MXN',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT,
        updated_at TEXT
    );
    """)

def sync_account_payment_status(*_: Any, **kwargs: Any) -> dict[str, Any]:
    return {
        "account_id": kwargs.get("account_id"),
        "provider_status": kwargs.get("provider_status") or "unknown",
        "synced": True,
        "mode": "rc_compatibility",
    }

class VerticalTransactionService:
    def list_transactions(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"items": [], "total": 0, "mode": "rc_compatibility"}

    def get_transaction(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"id": kwargs.get("transaction_id") or kwargs.get("id"), "status": "not_found"}

    def create_transaction(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"id": kwargs.get("id") or "txn_rc", "status": "created", **kwargs}

    def update_transaction(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"id": kwargs.get("transaction_id") or kwargs.get("id") or "txn_rc", "status": "updated", **kwargs}

    def __getattr__(self, name: str):
        def _method(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return {"operation": name, "status": "not_configured", "mode": "rc_compatibility"}
        return _method

vertical_transaction_service = VerticalTransactionService()
