from __future__ import annotations

from typing import Any

from .utils import from_json, hash_value, new_id, parse_iso, to_json, utcnow, utcnow_iso
from .world_class import execute, fetch_all, fetch_one, has_column, sparse_vector_from_text, table_exists, vector_similarity


_ALLOWED_DOMAINS = {"commercial", "operational", "legal", "support"}
_SOURCE_KIND_DEFAULT_SUPPORTS = {
    "config_seed": ["pricing", "schedule", "location", "faq", "support"],
    "catalog": ["pricing", "commercial", "support"],
    "policy": ["legal", "support", "payment"],
    "sop": ["operational", "support", "schedule"],
    "faq": ["faq", "support", "location"],
    "pdf": ["support", "faq"],
    "web_page": ["pricing", "support", "faq"],
    "url": ["pricing", "support", "faq"],
    "notion": ["support", "faq", "schedule"],
    "drive": ["support", "faq", "pricing"],
    "form": ["support", "faq", "operational"],
    "doc": ["support", "faq"],
    "import": ["support", "faq"],
}
_DOMAIN_DEFAULT_SUPPORTS = {
    "commercial": ["pricing", "faq", "support", "payment"],
    "operational": ["schedule", "support", "faq", "location"],
    "legal": ["payment", "support", "faq", "legal"],
    "support": ["faq", "support", "general"],
}
_TOPIC_DOMAIN_HINTS = {
    "pricing": "commercial",
    "payment": "legal",
    "schedule": "operational",
    "location": "operational",
    "faq": "support",
    "support": "support",
    "general": "support",
}


def ensure_knowledge_governance_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            title TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_uri TEXT,
            source_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            owner_type TEXT NOT NULL DEFAULT 'system',
            refresh_strategy TEXT NOT NULL DEFAULT 'manual',
            refresh_after TEXT,
            freshness_window_days INTEGER NOT NULL DEFAULT 30,
            current_version_id TEXT,
            invalidated_reason TEXT,
            tags_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, bot_id, source_key)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_documents_bot_domain ON knowledge_documents(organization_id, bot_id, domain, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_knowledge_documents_refresh ON knowledge_documents(organization_id, bot_id, status, refresh_after);

        CREATE TABLE IF NOT EXISTS knowledge_document_versions (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            content_text TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            vector_json TEXT NOT NULL DEFAULT '{}',
            source_snapshot_json TEXT NOT NULL DEFAULT '{}',
            supports_json TEXT NOT NULL DEFAULT '[]',
            extracted_entities_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            is_current INTEGER NOT NULL DEFAULT 1,
            freshness_status TEXT NOT NULL DEFAULT 'fresh',
            created_at TEXT NOT NULL,
            UNIQUE(document_id, version_number)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_document_versions_doc ON knowledge_document_versions(document_id, is_current, created_at DESC);

        CREATE TABLE IF NOT EXISTS knowledge_refresh_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            freshness_before TEXT,
            freshness_after TEXT,
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_refresh_events_doc ON knowledge_refresh_events(document_id, created_at DESC);
        """
    )


def _normalize_domain(domain: str | None) -> str:
    value = str(domain or "support").strip().lower()
    return value if value in _ALLOWED_DOMAINS else "support"


def _normalize_supports(supports: list[str] | None, *, domain: str, source_kind: str) -> list[str]:
    result: list[str] = []
    for item in (supports or []):
        token = str(item or "").strip().lower()
        if token and token not in result:
            result.append(token)
    for bucket in (_SOURCE_KIND_DEFAULT_SUPPORTS.get(source_kind, []), _DOMAIN_DEFAULT_SUPPORTS.get(domain, [])):
        for token in bucket:
            if token not in result:
                result.append(token)
    return result[:10]


def _freshness_status(*, updated_at: str | None, freshness_window_days: int) -> str:
    timestamp = parse_iso(updated_at)
    if timestamp is None:
        return "unknown"
    age_days = max(0.0, (utcnow() - timestamp).total_seconds() / 86400.0)
    if freshness_window_days <= 0:
        freshness_window_days = 1
    if age_days <= freshness_window_days * 0.6:
        return "fresh"
    if age_days <= freshness_window_days:
        return "aging"
    return "stale"


def _freshness_score(status: str) -> float:
    return {"fresh": 1.0, "aging": 0.72, "stale": 0.2, "unknown": 0.45}.get(status, 0.3)


def _version_supports(row: dict[str, Any]) -> list[str]:
    return [str(item).lower() for item in from_json(row.get("supports_json"), []) if item]


def _version_vector(content_text: str) -> dict[str, float]:
    return sparse_vector_from_text(content_text or "")


def _record_refresh_event(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    document_id: str,
    event_type: str,
    freshness_before: str | None,
    freshness_after: str | None,
    details: dict[str, Any] | None = None,
) -> None:
    if not table_exists(conn, "knowledge_refresh_events"):
        return
    event_id = new_id("krefresh")
    execute(
        conn,
        """
        INSERT INTO knowledge_refresh_events (
            id, organization_id, bot_id, document_id, event_type, freshness_before, freshness_after, details_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            organization_id,
            bot_id,
            document_id,
            event_type,
            freshness_before,
            freshness_after,
            to_json(details or {}),
            utcnow_iso(),
        ),
    )


def _current_version(conn, document_id: str) -> dict[str, Any] | None:
    return fetch_one(conn, "SELECT * FROM knowledge_document_versions WHERE document_id = ? AND is_current = 1 ORDER BY version_number DESC LIMIT 1", (document_id,))


def ingest_knowledge_document(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    title: str,
    source_kind: str,
    source_key: str,
    content_text: str,
    domain: str,
    source_uri: str | None = None,
    refresh_strategy: str = "manual",
    refresh_after: str | None = None,
    freshness_window_days: int = 30,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    supports: list[str] | None = None,
    owner_type: str = "system",
) -> dict[str, Any]:
    ensure_knowledge_governance_schema(conn)
    normalized_domain = _normalize_domain(domain)
    normalized_source_kind = str(source_kind or "import").strip().lower() or "import"
    normalized_supports = _normalize_supports(supports, domain=normalized_domain, source_kind=normalized_source_kind)
    rendered_text = str(content_text or "").strip()
    if not rendered_text:
        raise ValueError("content_text is required")
    freshness_window_days = max(1, int(freshness_window_days or 30))
    now = utcnow_iso()
    content_hash = hash_value(rendered_text)
    existing = fetch_one(
        conn,
        "SELECT * FROM knowledge_documents WHERE organization_id = ? AND bot_id = ? AND source_key = ?",
        (organization_id, bot_id, source_key),
    )
    if existing is None:
        document_id = new_id("kdoc")
        execute(
            conn,
            """
            INSERT INTO knowledge_documents (
                id, organization_id, bot_id, domain, title, source_kind, source_uri, source_key, status, owner_type,
                refresh_strategy, refresh_after, freshness_window_days, current_version_id, invalidated_reason,
                tags_json, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?)
            """,
            (
                document_id,
                organization_id,
                bot_id,
                normalized_domain,
                str(title or source_key),
                normalized_source_kind,
                source_uri,
                source_key,
                owner_type,
                refresh_strategy,
                refresh_after,
                freshness_window_days,
                to_json(tags or []),
                to_json(metadata or {}),
                now,
                now,
            ),
        )
        existing = fetch_one(conn, "SELECT * FROM knowledge_documents WHERE id = ?", (document_id,))
    else:
        document_id = existing["id"]
        execute(
            conn,
            """
            UPDATE knowledge_documents
            SET title = ?, domain = ?, source_kind = ?, source_uri = ?, status = 'active', invalidated_reason = NULL,
                refresh_strategy = ?, refresh_after = ?, freshness_window_days = ?, tags_json = ?, metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                str(title or source_key),
                normalized_domain,
                normalized_source_kind,
                source_uri,
                refresh_strategy,
                refresh_after,
                freshness_window_days,
                to_json(tags or []),
                to_json(metadata or {}),
                now,
                document_id,
            ),
        )
        existing = fetch_one(conn, "SELECT * FROM knowledge_documents WHERE id = ?", (document_id,))

    current_version = _current_version(conn, document_id)
    if current_version and current_version.get("content_hash") == content_hash:
        freshness_status = _freshness_status(updated_at=now, freshness_window_days=freshness_window_days)
        execute(
            conn,
            """
            UPDATE knowledge_document_versions
            SET freshness_status = ?, metadata_json = ?, supports_json = ?, source_snapshot_json = ?
            WHERE id = ?
            """,
            (
                freshness_status,
                to_json(metadata or {}),
                to_json(normalized_supports),
                to_json({"source_uri": source_uri, "source_kind": normalized_source_kind, "title": title}),
                current_version["id"],
            ),
        )
        execute(
            conn,
            "UPDATE knowledge_documents SET updated_at = ?, current_version_id = ? WHERE id = ?",
            (now, current_version["id"], document_id),
        )
        row = fetch_one(conn, "SELECT * FROM knowledge_documents WHERE id = ?", (document_id,)) or {}
        version = fetch_one(conn, "SELECT * FROM knowledge_document_versions WHERE id = ?", (current_version["id"],)) or {}
        return {"document": row, "version": version, "changed": False}

    previous_status = current_version.get("freshness_status") if current_version else None
    if current_version:
        execute(conn, "UPDATE knowledge_document_versions SET is_current = 0 WHERE document_id = ? AND is_current = 1", (document_id,))
        next_version = int(current_version.get("version_number") or 1) + 1
    else:
        next_version = 1
    freshness_status = _freshness_status(updated_at=now, freshness_window_days=freshness_window_days)
    version_id = new_id("kver")
    execute(
        conn,
        """
        INSERT INTO knowledge_document_versions (
            id, document_id, organization_id, bot_id, version_number, content_text, content_hash, vector_json,
            source_snapshot_json, supports_json, extracted_entities_json, metadata_json, is_current, freshness_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', ?, 1, ?, ?)
        """,
        (
            version_id,
            document_id,
            organization_id,
            bot_id,
            next_version,
            rendered_text,
            content_hash,
            to_json(_version_vector(rendered_text)),
            to_json({"source_uri": source_uri, "source_kind": normalized_source_kind, "title": title}),
            to_json(normalized_supports),
            to_json(metadata or {}),
            freshness_status,
            now,
        ),
    )
    execute(
        conn,
        "UPDATE knowledge_documents SET current_version_id = ?, updated_at = ?, status = 'active', invalidated_reason = NULL WHERE id = ?",
        (version_id, now, document_id),
    )
    _record_refresh_event(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        document_id=document_id,
        event_type="ingested" if next_version == 1 else "versioned",
        freshness_before=previous_status,
        freshness_after=freshness_status,
        details={"version_number": next_version, "source_key": source_key, "source_kind": normalized_source_kind},
    )
    row = fetch_one(conn, "SELECT * FROM knowledge_documents WHERE id = ?", (document_id,)) or {}
    version = fetch_one(conn, "SELECT * FROM knowledge_document_versions WHERE id = ?", (version_id,)) or {}
    return {"document": row, "version": version, "changed": True}


def invalidate_knowledge_document(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    source_key: str,
    reason: str,
) -> dict[str, Any] | None:
    ensure_knowledge_governance_schema(conn)
    row = fetch_one(
        conn,
        "SELECT * FROM knowledge_documents WHERE organization_id = ? AND bot_id = ? AND source_key = ?",
        (organization_id, bot_id, source_key),
    )
    if row is None:
        return None
    current_version = _current_version(conn, row["id"]) or {}
    execute(
        conn,
        "UPDATE knowledge_documents SET status = 'invalidated', invalidated_reason = ?, updated_at = ? WHERE id = ?",
        (reason, utcnow_iso(), row["id"]),
    )
    _record_refresh_event(
        conn,
        organization_id=organization_id,
        bot_id=bot_id,
        document_id=row["id"],
        event_type="invalidated",
        freshness_before=current_version.get("freshness_status"),
        freshness_after="invalidated",
        details={"reason": reason, "source_key": source_key},
    )
    return fetch_one(conn, "SELECT * FROM knowledge_documents WHERE id = ?", (row["id"],))


def list_refresh_candidates(conn, *, organization_id: str, bot_id: str, limit: int = 20) -> list[dict[str, Any]]:
    ensure_knowledge_governance_schema(conn)
    now = utcnow_iso()
    rows = fetch_all(
        conn,
        """
        SELECT d.*, v.freshness_status, v.version_number
        FROM knowledge_documents d
        LEFT JOIN knowledge_document_versions v ON v.id = d.current_version_id
        WHERE d.organization_id = ? AND d.bot_id = ? AND d.status = 'active'
        ORDER BY d.updated_at ASC
        """,
        (organization_id, bot_id),
    )
    candidates: list[dict[str, Any]] = []
    for row in rows:
        refresh_due = False
        refresh_after = row.get("refresh_after")
        if refresh_after and parse_iso(refresh_after) and parse_iso(refresh_after) <= parse_iso(now):
            refresh_due = True
        freshness_status = row.get("freshness_status") or _freshness_status(
            updated_at=row.get("updated_at"),
            freshness_window_days=int(row.get("freshness_window_days") or 30),
        )
        if refresh_due or freshness_status in {"aging", "stale"}:
            candidates.append(
                {
                    **row,
                    "refresh_due": refresh_due,
                    "freshness_status": freshness_status,
                    "refresh_priority": 100 if freshness_status == "stale" else (70 if refresh_due else 50),
                }
            )
    candidates.sort(key=lambda item: (-(item.get("refresh_priority") or 0), item.get("updated_at") or ""))
    return candidates[:limit]


def sync_config_knowledge(conn, *, organization_id: str, bot_id: str, bot_config: dict[str, Any]) -> dict[str, Any]:
    ensure_knowledge_governance_schema(conn)
    business = dict((bot_config or {}).get("business_knowledge") or {})
    active_source_keys: set[str] = set()
    ingested: list[dict[str, Any]] = []

    def _ingest(source_key: str, *, title: str, content_text: str, domain: str, supports: list[str], tags: list[str] | None = None):
        active_source_keys.add(source_key)
        ingested.append(
            ingest_knowledge_document(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                title=title,
                source_kind="config_seed",
                source_key=source_key,
                content_text=content_text,
                domain=domain,
                source_uri=f"config://{source_key}",
                refresh_strategy="on_config_change",
                refresh_after=None,
                freshness_window_days=30 if domain != "legal" else 14,
                metadata={"seeded_from": "bot_config"},
                supports=supports,
                tags=tags or [],
            )
        )

    hours = str(business.get("hours") or "").strip()
    if hours:
        _ingest("config.hours", title="Business hours", content_text=hours, domain="operational", supports=["schedule", "faq"], tags=["hours"])
    location = str(business.get("location") or "").strip()
    if location:
        _ingest("config.location", title="Business location", content_text=location, domain="operational", supports=["location", "faq"], tags=["location"])
    for idx, item in enumerate(business.get("services") or []):
        value = str(item or "").strip()
        if value:
            _ingest(f"config.service.{idx}", title=f"Service {idx + 1}", content_text=value, domain="commercial", supports=["faq", "support"], tags=["service"])
    for idx, item in enumerate(business.get("prices") or []):
        if isinstance(item, dict):
            content_text = f"{item.get('name', 'Servicio')}: {item.get('price', '')}".strip()
        else:
            content_text = str(item or "").strip()
        if content_text:
            _ingest(f"config.price.{idx}", title=f"Price {idx + 1}", content_text=content_text, domain="commercial", supports=["pricing", "payment"], tags=["pricing"])
    for idx, item in enumerate(business.get("faqs") or []):
        if isinstance(item, dict):
            content_text = f"Q: {item.get('q', '')} A: {item.get('a', '')}".strip()
        else:
            content_text = str(item or "").strip()
        if content_text:
            _ingest(f"config.faq.{idx}", title=f"FAQ {idx + 1}", content_text=content_text, domain="support", supports=["faq", "support"], tags=["faq"])
    for idx, item in enumerate(business.get("policies") or []):
        if isinstance(item, dict):
            content_text = f"{item.get('name', 'Policy')}: {item.get('content', '')}".strip()
        else:
            content_text = str(item or "").strip()
        if content_text:
            _ingest(f"config.policy.{idx}", title=f"Policy {idx + 1}", content_text=content_text, domain="legal", supports=["payment", "support", "faq"], tags=["policy"])

    existing = fetch_all(
        conn,
        "SELECT source_key FROM knowledge_documents WHERE organization_id = ? AND bot_id = ? AND source_kind = 'config_seed' AND status = 'active'",
        (organization_id, bot_id),
    )
    invalidated: list[str] = []
    for row in existing:
        source_key = str(row.get("source_key") or "")
        if source_key and source_key not in active_source_keys:
            invalidate_knowledge_document(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                source_key=source_key,
                reason="config_removed_or_changed",
            )
            invalidated.append(source_key)

    return {
        "ingested_count": len(ingested),
        "invalidated_source_keys": invalidated,
        "active_source_keys": sorted(active_source_keys),
    }


def _search_rows(conn, *, organization_id: str, bot_id: str) -> list[dict[str, Any]]:
    ensure_knowledge_governance_schema(conn)
    if table_exists(conn, "knowledge_source_publications"):
        return fetch_all(
            conn,
            """
            SELECT d.id AS document_id, d.domain, d.title, d.source_kind, d.source_uri, d.source_key, d.status, d.refresh_after,
                   d.refresh_strategy, d.freshness_window_days, d.invalidated_reason, d.tags_json, d.metadata_json AS document_metadata_json,
                   d.updated_at AS document_updated_at, v.id AS version_id, v.version_number, v.content_text, v.vector_json,
                   v.source_snapshot_json, v.supports_json, v.metadata_json AS version_metadata_json, v.freshness_status, v.created_at AS version_created_at,
                   p.source_connection_id, p.external_item_key, p.state AS publication_state, p.validation_status,
                   p.owner_user_id, p.source_updated_at, p.published_at, p.last_synced_at, p.metadata_json AS publication_metadata_json
            FROM knowledge_documents d
            JOIN knowledge_document_versions v ON v.id = d.current_version_id
            LEFT JOIN knowledge_source_publications p ON p.knowledge_document_id = d.id
            WHERE d.organization_id = ? AND d.bot_id = ? AND d.status = 'active' AND v.is_current = 1
            ORDER BY d.updated_at DESC
            """,
            (organization_id, bot_id),
        )
    return fetch_all(
        conn,
        """
        SELECT d.id AS document_id, d.domain, d.title, d.source_kind, d.source_uri, d.source_key, d.status, d.refresh_after,
               d.refresh_strategy, d.freshness_window_days, d.invalidated_reason, d.tags_json, d.metadata_json AS document_metadata_json,
               d.updated_at AS document_updated_at, v.id AS version_id, v.version_number, v.content_text, v.vector_json,
               v.source_snapshot_json, v.supports_json, v.metadata_json AS version_metadata_json, v.freshness_status, v.created_at AS version_created_at
        FROM knowledge_documents d
        JOIN knowledge_document_versions v ON v.id = d.current_version_id
        WHERE d.organization_id = ? AND d.bot_id = ? AND d.status = 'active' AND v.is_current = 1
        ORDER BY d.updated_at DESC
        """,
        (organization_id, bot_id),
    )


def search_governed_knowledge(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    query: str,
    intent: str | None = None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    rows = _search_rows(conn, organization_id=organization_id, bot_id=bot_id)
    query_vector = _version_vector(query or "")
    domain_hint = _TOPIC_DOMAIN_HINTS.get(str(intent or "").strip().lower())
    scored: list[dict[str, Any]] = []
    for row in rows:
        supports = _version_supports(row)
        similarity = vector_similarity(query_vector, from_json(row.get("vector_json"), {}))
        freshness_status = row.get("freshness_status") or _freshness_status(
            updated_at=row.get("version_created_at") or row.get("document_updated_at"),
            freshness_window_days=int(row.get("freshness_window_days") or 30),
        )
        domain_boost = 0.18 if domain_hint and row.get("domain") == domain_hint else 0.0
        support_boost = 0.12 if intent and str(intent).lower() in supports else 0.0
        freshness_boost = 0.2 * _freshness_score(freshness_status)
        if similarity <= 0 and str(query or "").strip() and (domain_boost + support_boost) <= 0:
            continue
        score = round(float(similarity) + domain_boost + support_boost + freshness_boost, 4)
        publication_metadata = from_json(row.get("publication_metadata_json"), {})
        scored.append(
            {
                **row,
                "supports": supports,
                "similarity": round(float(similarity), 4),
                "freshness_status": freshness_status,
                "freshness_score": round(_freshness_score(freshness_status), 3),
                "score": score,
                "document_metadata": from_json(row.get("document_metadata_json"), {}),
                "version_metadata": from_json(row.get("version_metadata_json"), {}),
                "publication_metadata": publication_metadata,
                "traceability": {
                    "document_id": row.get("document_id"),
                    "version_id": row.get("version_id"),
                    "version_number": row.get("version_number"),
                    "domain": row.get("domain"),
                    "source_kind": row.get("source_kind"),
                    "source_key": row.get("source_key"),
                    "source_uri": row.get("source_uri"),
                    "freshness_status": freshness_status,
                    "updated_at": row.get("document_updated_at"),
                    "source_connection_id": row.get("source_connection_id") or publication_metadata.get("source_connection_id"),
                    "external_item_key": row.get("external_item_key"),
                    "publication_state": row.get("publication_state") or publication_metadata.get("state"),
                    "validation_status": row.get("validation_status") or publication_metadata.get("validation_status"),
                    "owner_user_id": row.get("owner_user_id") or publication_metadata.get("owner_user_id"),
                    "source_updated_at": row.get("source_updated_at") or publication_metadata.get("source_updated_at"),
                    "published_at": row.get("published_at") or publication_metadata.get("published_at"),
                    "last_synced_at": row.get("last_synced_at") or publication_metadata.get("last_synced_at"),
                },
            }
        )
    scored.sort(key=lambda item: (float(item.get("score") or 0), float(item.get("similarity") or 0)), reverse=True)
    return scored[:limit]


def governed_knowledge_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    domain_counts: dict[str, int] = {}
    freshness_counts: dict[str, int] = {}
    trace: list[dict[str, Any]] = []
    for row in rows:
        domain = str(row.get("domain") or "support")
        freshness = str(row.get("freshness_status") or "unknown")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        freshness_counts[freshness] = freshness_counts.get(freshness, 0) + 1
        trace.append(dict(row.get("traceability") or {}))
    overall_freshness = "fresh"
    if freshness_counts.get("stale"):
        overall_freshness = "stale"
    elif freshness_counts.get("aging"):
        overall_freshness = "aging"
    elif freshness_counts.get("unknown") and not freshness_counts.get("fresh"):
        overall_freshness = "unknown"
    return {
        "domain_counts": domain_counts,
        "freshness_counts": freshness_counts,
        "overall_freshness": overall_freshness,
        "traceability": trace[:8],
    }
