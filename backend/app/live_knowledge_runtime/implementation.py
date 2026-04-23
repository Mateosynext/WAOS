from __future__ import annotations

from ..schema_sql import apply_migration_sql

from dataclasses import dataclass
from typing import Any

from ..knowledge_runtime import ensure_knowledge_governance_schema, ingest_knowledge_document, invalidate_knowledge_document
from ..utils import from_json, hash_value, new_id, parse_iso, slugify, to_json, utcnow_iso
from ..world_class import execute, fetch_all, fetch_one

_ALLOWED_CONNECTORS = {"notion", "drive", "url", "pdf", "form"}
_ALLOWED_WATCH_MODES = {"manual", "polling", "webhook"}
_ALLOWED_PUBLISH_POLICIES = {"auto_publish", "manual_review", "disabled"}


@dataclass(frozen=True)
class NormalizedSourceItem:
    external_item_key: str
    title: str
    content_text: str
    source_uri: str | None
    domain: str
    supports: list[str]
    tags: list[str]
    source_updated_at: str | None
    metadata: dict[str, Any]


class BaseKnowledgeConnector:
    key = "base"
    source_kind = "import"

    def normalize_item(self, source: dict[str, Any], raw_item: dict[str, Any]) -> NormalizedSourceItem:
        title = str(raw_item.get("title") or raw_item.get("name") or source.get("label") or source.get("source_key") or "knowledge item").strip()
        content_text = self._content_text(raw_item)
        source_uri = str(raw_item.get("source_uri") or raw_item.get("url") or source.get("source_uri") or "").strip() or None
        supports = _normalize_tokens(raw_item.get("supports") or (from_json(source.get("config_json"), {}) or {}).get("supports") or [])
        tags = _normalize_tokens(raw_item.get("tags") or (from_json(source.get("config_json"), {}) or {}).get("tags") or [])
        metadata = dict(from_json(source.get("metadata_json"), {}))
        metadata.update(dict(raw_item.get("metadata") or {}))
        if raw_item.get("owner_user_id"):
            metadata.setdefault("owner_user_id", raw_item.get("owner_user_id"))
        domain = _infer_domain(raw_item.get("domain"), title=title, content_text=content_text, supports=supports, tags=tags)
        if not supports:
            supports = _infer_supports(title=title, content_text=content_text, tags=tags, domain=domain)
        external_item_key = str(raw_item.get("external_item_key") or raw_item.get("id") or _stable_key(title=title, source_uri=source_uri, content_text=content_text)).strip()
        source_updated_at = str(raw_item.get("source_updated_at") or raw_item.get("updated_at") or raw_item.get("modified_at") or "").strip() or None
        return NormalizedSourceItem(
            external_item_key=external_item_key,
            title=title,
            content_text=content_text,
            source_uri=source_uri,
            domain=domain,
            supports=supports,
            tags=tags,
            source_updated_at=source_updated_at,
            metadata=metadata,
        )

    def _content_text(self, raw_item: dict[str, Any]) -> str:
        for key in ("content_text", "extracted_text", "plain_text", "body", "text", "summary"):
            value = raw_item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        blocks = raw_item.get("blocks") or raw_item.get("sections") or raw_item.get("pages") or []
        if isinstance(blocks, list):
            parts = [str(item).strip() for item in blocks if str(item).strip()]
            if parts:
                return "\n".join(parts)
        if isinstance(raw_item.get("content"), dict):
            lines: list[str] = []
            for key, value in raw_item["content"].items():
                value_str = str(value).strip()
                if value_str:
                    lines.append(f"{key}: {value_str}")
            if lines:
                return "\n".join(lines)
        return str(raw_item.get("content") or "").strip()


class NotionConnector(BaseKnowledgeConnector):
    key = "notion"
    source_kind = "notion"


class DriveConnector(BaseKnowledgeConnector):
    key = "drive"
    source_kind = "drive"


class UrlConnector(BaseKnowledgeConnector):
    key = "url"
    source_kind = "url"


class PdfConnector(BaseKnowledgeConnector):
    key = "pdf"
    source_kind = "pdf"


class FormConnector(BaseKnowledgeConnector):
    key = "form"
    source_kind = "form"

    def _content_text(self, raw_item: dict[str, Any]) -> str:
        answers = raw_item.get("answers")
        if isinstance(answers, dict):
            lines = []
            for key, value in answers.items():
                value_str = str(value).strip()
                if value_str:
                    lines.append(f"{key}: {value_str}")
            if lines:
                return "\n".join(lines)
        return super()._content_text(raw_item)


_CONNECTORS = {
    "notion": NotionConnector(),
    "drive": DriveConnector(),
    "url": UrlConnector(),
    "pdf": PdfConnector(),
    "form": FormConnector(),
}


def ensure_live_knowledge_ingestion_schema(conn) -> None:
    ensure_knowledge_governance_schema(conn)
    apply_migration_sql(conn, '009_live_knowledge_ingestion.sql')


def _stable_key(*, title: str, source_uri: str | None, content_text: str) -> str:
    base = source_uri or title or content_text[:80]
    slug = slugify(base)[:40]
    digest = hash_value(f"{title}|{source_uri}|{content_text[:120]}")[:10]
    return f"{slug or 'item'}-{digest}"


def _normalize_tokens(values: Any) -> list[str]:
    if isinstance(values, str):
        values = [values]
    result: list[str] = []
    for item in values or []:
        token = str(item or "").strip().lower()
        if token and token not in result:
            result.append(token)
    return result[:12]


def _infer_domain(domain: Any, *, title: str, content_text: str, supports: list[str], tags: list[str]) -> str:
    explicit = str(domain or "").strip().lower()
    if explicit in {"commercial", "operational", "legal", "support"}:
        return explicit
    signal = " ".join([title, content_text, " ".join(supports), " ".join(tags)]).lower()
    if any(token in signal for token in ["precio", "price", "$", "promoción", "promotion", "venta", "sale"]):
        return "commercial"
    if any(token in signal for token in ["horario", "hours", "agenda", "appointment", "schedule", "ubicación", "location"]):
        return "operational"
    if any(token in signal for token in ["policy", "política", "refund", "terms", "privacy", "legal", "payment"]):
        return "legal"
    return "support"


def _infer_supports(*, title: str, content_text: str, tags: list[str], domain: str) -> list[str]:
    signal = " ".join([title, content_text, " ".join(tags)]).lower()
    supports: list[str] = []
    mapping = {
        "pricing": ["precio", "price", "$", "mxn", "usd", "promotion", "promoción"],
        "schedule": ["horario", "hours", "appointment", "agenda", "schedule", "reagenda"],
        "location": ["ubicación", "location", "dirección", "address", "maps"],
        "payment": ["payment", "pago", "refund", "invoice", "receipt"],
        "faq": ["faq", "pregunta", "question"],
        "support": ["support", "soporte", "help", "ayuda"],
    }
    for support, keywords in mapping.items():
        if any(token in signal for token in keywords):
            supports.append(support)
    if not supports:
        supports.append("support")
    if domain == "commercial" and "pricing" not in supports:
        supports.append("pricing")
    if domain == "operational" and "schedule" not in supports:
        supports.append("schedule")
    if domain == "legal" and "payment" not in supports:
        supports.append("payment")
    if "faq" not in supports:
        supports.append("faq")
    ordered: list[str] = []
    for item in supports:
        if item not in ordered:
            ordered.append(item)
    return ordered[:8]


def _normalize_connector_key(value: str | None) -> str:
    key = str(value or "url").strip().lower()
    return key if key in _ALLOWED_CONNECTORS else "url"


def _normalize_watch_mode(value: str | None) -> str:
    mode = str(value or "manual").strip().lower()
    return mode if mode in _ALLOWED_WATCH_MODES else "manual"


def _normalize_publish_policy(value: str | None) -> str:
    policy = str(value or "auto_publish").strip().lower()
    return policy if policy in _ALLOWED_PUBLISH_POLICIES else "auto_publish"


def _validation_policy(source: dict[str, Any]) -> dict[str, Any]:
    policy = dict(from_json(source.get("validation_policy_json"), {}))
    policy.setdefault("min_chars", 24)
    policy.setdefault("require_title", False)
    return policy


def _connector(source: dict[str, Any]) -> BaseKnowledgeConnector:
    return _CONNECTORS[_normalize_connector_key(source.get("connector_key"))]


def upsert_knowledge_source_connection(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    source_key: str,
    connector_key: str,
    label: str,
    source_uri: str | None = None,
    owner_user_id: str | None = None,
    watch_mode: str = "manual",
    sync_interval_minutes: int = 60,
    publish_policy: str = "auto_publish",
    validation_policy: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_live_knowledge_ingestion_schema(conn)
    now = utcnow_iso()
    existing = fetch_one(
        conn,
        "SELECT * FROM knowledge_source_connections WHERE organization_id = ? AND bot_id = ? AND source_key = ?",
        (organization_id, bot_id, source_key),
    )
    if existing is None:
        source_id = new_id("ksrc")
        execute(
            conn,
            """
            INSERT INTO knowledge_source_connections (
                id, organization_id, bot_id, source_key, connector_key, label, source_uri, owner_user_id, status,
                watch_mode, sync_interval_minutes, publish_policy, validation_policy_json, config_json, metadata_json,
                current_snapshot_hash, last_seen_source_updated_at, last_synced_at, last_published_at, last_error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?, ?)
            """,
            (
                source_id,
                organization_id,
                bot_id,
                source_key,
                _normalize_connector_key(connector_key),
                str(label or source_key),
                source_uri,
                owner_user_id,
                _normalize_watch_mode(watch_mode),
                max(1, int(sync_interval_minutes or 60)),
                _normalize_publish_policy(publish_policy),
                to_json(validation_policy or {}),
                to_json(config or {}),
                to_json(metadata or {}),
                now,
                now,
            ),
        )
    else:
        source_id = existing["id"]
        execute(
            conn,
            """
            UPDATE knowledge_source_connections
            SET connector_key = ?, label = ?, source_uri = ?, owner_user_id = ?, status = 'active', watch_mode = ?,
                sync_interval_minutes = ?, publish_policy = ?, validation_policy_json = ?, config_json = ?, metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                _normalize_connector_key(connector_key),
                str(label or source_key),
                source_uri,
                owner_user_id,
                _normalize_watch_mode(watch_mode),
                max(1, int(sync_interval_minutes or 60)),
                _normalize_publish_policy(publish_policy),
                to_json(validation_policy or {}),
                to_json(config or {}),
                to_json(metadata or {}),
                now,
                source_id,
            ),
        )
    return fetch_one(conn, "SELECT * FROM knowledge_source_connections WHERE id = ?", (source_id,)) or {}


def _validate_item(item: NormalizedSourceItem, policy: dict[str, Any], *, owner_user_id: str | None) -> dict[str, Any]:
    min_chars = max(1, int(policy.get("min_chars") or 24))
    require_title = bool(policy.get("require_title"))
    reasons: list[str] = []
    status = "passed"
    content_text = str(item.content_text or "").strip()
    if require_title and not item.title:
        status = "review_required"
        reasons.append("missing_title")
    if not content_text:
        return {"status": "rejected", "reasons": ["missing_content"]}
    if len(content_text) < min_chars:
        status = "review_required"
        reasons.append("content_too_short")
    if item.source_updated_at and parse_iso(item.source_updated_at) is None:
        status = "review_required"
        reasons.append("invalid_source_updated_at")
    if not owner_user_id:
        reasons.append("owner_missing")
    return {"status": status, "reasons": reasons}


def _upsert_publication(
    conn,
    *,
    organization_id: str,
    bot_id: str,
    source_connection_id: str,
    external_item_key: str,
    knowledge_document_id: str | None,
    knowledge_version_id: str | None,
    source_kind: str,
    source_uri: str | None,
    state: str,
    validation_status: str,
    owner_user_id: str | None,
    source_updated_at: str | None,
    published_at: str | None,
    last_synced_at: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = utcnow_iso()
    existing = fetch_one(
        conn,
        "SELECT * FROM knowledge_source_publications WHERE source_connection_id = ? AND external_item_key = ?",
        (source_connection_id, external_item_key),
    )
    if existing is None:
        publication_id = new_id("kpub")
        execute(
            conn,
            """
            INSERT INTO knowledge_source_publications (
                id, organization_id, bot_id, source_connection_id, external_item_key, knowledge_document_id, knowledge_version_id,
                source_kind, source_uri, state, validation_status, owner_user_id, source_updated_at, published_at, last_synced_at,
                metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                publication_id,
                organization_id,
                bot_id,
                source_connection_id,
                external_item_key,
                knowledge_document_id,
                knowledge_version_id,
                source_kind,
                source_uri,
                state,
                validation_status,
                owner_user_id,
                source_updated_at,
                published_at,
                last_synced_at,
                to_json(metadata or {}),
                now,
                now,
            ),
        )
    else:
        publication_id = existing["id"]
        execute(
            conn,
            """
            UPDATE knowledge_source_publications
            SET knowledge_document_id = ?, knowledge_version_id = ?, source_kind = ?, source_uri = ?, state = ?, validation_status = ?,
                owner_user_id = ?, source_updated_at = ?, published_at = ?, last_synced_at = ?, metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                knowledge_document_id,
                knowledge_version_id,
                source_kind,
                source_uri,
                state,
                validation_status,
                owner_user_id,
                source_updated_at,
                published_at,
                last_synced_at,
                to_json(metadata or {}),
                now,
                publication_id,
            ),
        )
    return fetch_one(conn, "SELECT * FROM knowledge_source_publications WHERE id = ?", (publication_id,)) or {}


def _insert_sync_item(
    conn,
    *,
    sync_run_id: str,
    source_connection_id: str,
    external_item_key: str,
    title: str,
    source_uri: str | None,
    validation_status: str,
    publication_state: str,
    change_status: str,
    knowledge_document_id: str | None,
    knowledge_version_id: str | None,
    details: dict[str, Any] | None = None,
) -> None:
    execute(
        conn,
        """
        INSERT INTO knowledge_source_sync_items (
            id, sync_run_id, source_connection_id, external_item_key, title, source_uri, validation_status,
            publication_state, change_status, knowledge_document_id, knowledge_version_id, details_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("ksi"),
            sync_run_id,
            source_connection_id,
            external_item_key,
            title,
            source_uri,
            validation_status,
            publication_state,
            change_status,
            knowledge_document_id,
            knowledge_version_id,
            to_json(details or {}),
            utcnow_iso(),
        ),
    )


def list_knowledge_source_connections(conn, *, organization_id: str, bot_id: str | None = None) -> list[dict[str, Any]]:
    ensure_live_knowledge_ingestion_schema(conn)
    params: list[Any] = [organization_id]
    where = ["organization_id = ?"]
    if bot_id:
        where.append("bot_id = ?")
        params.append(bot_id)
    rows = fetch_all(
        conn,
        f"SELECT * FROM knowledge_source_connections WHERE {' AND '.join(where)} ORDER BY updated_at DESC",
        tuple(params),
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        last_run = fetch_one(conn, "SELECT * FROM knowledge_source_sync_runs WHERE source_connection_id = ? ORDER BY started_at DESC LIMIT 1", (row["id"],))
        counts = fetch_one(
            conn,
            "SELECT COUNT(*) AS total, SUM(CASE WHEN state = 'published' THEN 1 ELSE 0 END) AS published_count, SUM(CASE WHEN state = 'review_required' THEN 1 ELSE 0 END) AS review_count FROM knowledge_source_publications WHERE source_connection_id = ?",
            (row["id"],),
        ) or {"total": 0, "published_count": 0, "review_count": 0}
        items.append(
            {
                **row,
                "validation_policy": from_json(row.get("validation_policy_json"), {}),
                "config": from_json(row.get("config_json"), {}),
                "metadata": from_json(row.get("metadata_json"), {}),
                "last_run": last_run,
                "publication_counts": {
                    "total": int(counts.get("total") or 0),
                    "published": int(counts.get("published_count") or 0),
                    "review_required": int(counts.get("review_count") or 0),
                },
            }
        )
    return items


def list_knowledge_source_runs(conn, *, source_connection_id: str, limit: int = 20) -> list[dict[str, Any]]:
    ensure_live_knowledge_ingestion_schema(conn)
    rows = fetch_all(
        conn,
        "SELECT * FROM knowledge_source_sync_runs WHERE source_connection_id = ? ORDER BY started_at DESC LIMIT ?",
        (source_connection_id, max(1, int(limit or 20))),
    )
    return [{**row, "details": from_json(row.get("details_json"), {})} for row in rows]


def _current_publication_map(conn, *, source_connection_id: str) -> dict[str, dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM knowledge_source_publications WHERE source_connection_id = ?", (source_connection_id,))
    return {str(row.get("external_item_key")): row for row in rows if row.get("external_item_key")}


def run_knowledge_source_sync(
    conn,
    *,
    source_connection_id: str,
    trigger_kind: str = "manual",
    items: list[dict[str, Any]] | None = None,
    full_refresh: bool = True,
    validate_only: bool = False,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_live_knowledge_ingestion_schema(conn)
    source = fetch_one(conn, "SELECT * FROM knowledge_source_connections WHERE id = ?", (source_connection_id,))
    if source is None:
        raise ValueError("source_connection_id not found")
    started_at = utcnow_iso()
    run_id = new_id("ksrun")
    execute(
        conn,
        """
        INSERT INTO knowledge_source_sync_runs (
            id, organization_id, bot_id, source_connection_id, trigger_kind, status, full_refresh, validate_only,
            items_seen, items_published, items_skipped, items_invalidated, snapshot_hash, details_json, error_text, started_at, finished_at
        ) VALUES (?, ?, ?, ?, ?, 'running', ?, ?, 0, 0, 0, 0, NULL, ?, NULL, ?, NULL)
        """,
        (
            run_id,
            source["organization_id"],
            source["bot_id"],
            source_connection_id,
            str(trigger_kind or "manual"),
            1 if full_refresh else 0,
            1 if validate_only else 0,
            to_json(metadata or {}),
            started_at,
        ),
    )
    connector = _connector(source)
    policy = _validation_policy(source)
    owner_user_id = source.get("owner_user_id")
    normalized_items: list[NormalizedSourceItem] = []
    snapshot_inputs: list[str] = []
    published_count = 0
    skipped_count = 0
    invalidated_count = 0
    latest_source_updated_at: str | None = None
    current_publications = _current_publication_map(conn, source_connection_id=source_connection_id)
    seen_keys: set[str] = set()
    try:
        for raw in list(items or []):
            item = connector.normalize_item(source, dict(raw or {}))
            normalized_items.append(item)
            snapshot_inputs.append(f"{item.external_item_key}:{hash_value(item.content_text)}")
            if item.source_updated_at and (latest_source_updated_at is None or str(item.source_updated_at) > str(latest_source_updated_at)):
                latest_source_updated_at = item.source_updated_at
            seen_keys.add(item.external_item_key)
            validation = _validate_item(item, policy, owner_user_id=owner_user_id)
            validation_status = validation["status"]
            publication_state = "review_required" if validation_status == "review_required" else ("rejected" if validation_status == "rejected" else "published")
            change_status = "unchanged"
            document_id = None
            version_id = None
            published_at = None
            details = {
                "reasons": validation.get("reasons") or [],
                "source_updated_at": item.source_updated_at,
                "supports": item.supports,
                "tags": item.tags,
                "source_connection_id": source_connection_id,
                "source_sync_run_id": run_id,
                "owner_user_id": owner_user_id,
                **item.metadata,
            }
            if source.get("publish_policy") == "disabled" or validate_only:
                publication_state = "review_required" if validation_status != "rejected" else "rejected"
                skipped_count += 1
            elif source.get("publish_policy") == "manual_review" or validation_status != "passed":
                skipped_count += 1
            else:
                ingest_result = ingest_knowledge_document(
                    conn,
                    organization_id=source["organization_id"],
                    bot_id=source["bot_id"],
                    title=item.title,
                    source_kind=connector.source_kind,
                    source_key=f"live.{source_connection_id}.{item.external_item_key}",
                    content_text=item.content_text,
                    domain=item.domain,
                    source_uri=item.source_uri,
                    refresh_strategy=f"continuous_{source.get('watch_mode') or 'manual'}",
                    refresh_after=None,
                    freshness_window_days=int((from_json(source.get("config_json"), {}) or {}).get("freshness_window_days") or 14),
                    tags=item.tags,
                    metadata={**details, "publication_state": "published"},
                    supports=item.supports,
                    owner_type="integration",
                )
                document = dict(ingest_result.get("document") or {})
                version = dict(ingest_result.get("version") or {})
                document_id = document.get("id")
                version_id = version.get("id")
                change_status = "versioned" if ingest_result.get("changed") else "up_to_date"
                publication_state = "published"
                published_at = utcnow_iso()
                published_count += 1
            publication = _upsert_publication(
                conn,
                organization_id=source["organization_id"],
                bot_id=source["bot_id"],
                source_connection_id=source_connection_id,
                external_item_key=item.external_item_key,
                knowledge_document_id=document_id,
                knowledge_version_id=version_id,
                source_kind=connector.source_kind,
                source_uri=item.source_uri,
                state=publication_state,
                validation_status=validation_status,
                owner_user_id=owner_user_id,
                source_updated_at=item.source_updated_at,
                published_at=published_at,
                last_synced_at=started_at,
                metadata=details,
            )
            if publication and not document_id:
                document_id = publication.get("knowledge_document_id")
                version_id = publication.get("knowledge_version_id")
            _insert_sync_item(
                conn,
                sync_run_id=run_id,
                source_connection_id=source_connection_id,
                external_item_key=item.external_item_key,
                title=item.title,
                source_uri=item.source_uri,
                validation_status=validation_status,
                publication_state=publication_state,
                change_status=change_status,
                knowledge_document_id=document_id,
                knowledge_version_id=version_id,
                details=details,
            )
        if full_refresh:
            for external_item_key, publication in current_publications.items():
                if external_item_key in seen_keys:
                    continue
                if publication.get("knowledge_document_id"):
                    invalidate_knowledge_document(
                        conn,
                        organization_id=source["organization_id"],
                        bot_id=source["bot_id"],
                        source_key=f"live.{source_connection_id}.{external_item_key}",
                        reason="source_deleted_or_missing",
                    )
                _upsert_publication(
                    conn,
                    organization_id=source["organization_id"],
                    bot_id=source["bot_id"],
                    source_connection_id=source_connection_id,
                    external_item_key=external_item_key,
                    knowledge_document_id=publication.get("knowledge_document_id"),
                    knowledge_version_id=publication.get("knowledge_version_id"),
                    source_kind=publication.get("source_kind") or connector.source_kind,
                    source_uri=publication.get("source_uri"),
                    state="invalidated",
                    validation_status=publication.get("validation_status") or "passed",
                    owner_user_id=publication.get("owner_user_id"),
                    source_updated_at=publication.get("source_updated_at"),
                    published_at=publication.get("published_at"),
                    last_synced_at=started_at,
                    metadata={**from_json(publication.get("metadata_json"), {}), "invalidated_reason": "source_deleted_or_missing", "source_sync_run_id": run_id},
                )
                invalidated_count += 1
        snapshot_hash = hash_value("|".join(sorted(snapshot_inputs))) if snapshot_inputs else None
        finished_at = utcnow_iso()
        execute(
            conn,
            """
            UPDATE knowledge_source_sync_runs
            SET status = ?, items_seen = ?, items_published = ?, items_skipped = ?, items_invalidated = ?, snapshot_hash = ?, details_json = ?, finished_at = ?
            WHERE id = ?
            """,
            (
                "completed_with_warnings" if skipped_count or invalidated_count else "completed",
                len(normalized_items),
                published_count,
                skipped_count,
                invalidated_count,
                snapshot_hash,
                to_json({**(metadata or {}), "connector_key": source.get("connector_key"), "publish_policy": source.get("publish_policy")}),
                finished_at,
                run_id,
            ),
        )
        execute(
            conn,
            """
            UPDATE knowledge_source_connections
            SET current_snapshot_hash = ?, last_seen_source_updated_at = ?, last_synced_at = ?,
                last_published_at = CASE WHEN ? > 0 THEN ? ELSE last_published_at END,
                last_error = NULL, status = 'active', updated_at = ?
            WHERE id = ?
            """,
            (
                snapshot_hash,
                latest_source_updated_at,
                finished_at,
                published_count,
                finished_at,
                finished_at,
                source_connection_id,
            ),
        )
    except Exception as exc:
        finished_at = utcnow_iso()
        execute(conn, "UPDATE knowledge_source_sync_runs SET status = 'failed', error_text = ?, finished_at = ? WHERE id = ?", (str(exc), finished_at, run_id))
        execute(conn, "UPDATE knowledge_source_connections SET status = 'error', last_error = ?, last_synced_at = ?, updated_at = ? WHERE id = ?", (str(exc), finished_at, finished_at, source_connection_id))
        raise
    run_row = fetch_one(conn, "SELECT * FROM knowledge_source_sync_runs WHERE id = ?", (run_id,)) or {}
    source_row = fetch_one(conn, "SELECT * FROM knowledge_source_connections WHERE id = ?", (source_connection_id,)) or {}
    publications = fetch_all(conn, "SELECT * FROM knowledge_source_publications WHERE source_connection_id = ? ORDER BY updated_at DESC", (source_connection_id,))
    return {
        "source": {
            **source_row,
            "validation_policy": from_json(source_row.get("validation_policy_json"), {}),
            "config": from_json(source_row.get("config_json"), {}),
            "metadata": from_json(source_row.get("metadata_json"), {}),
        },
        "run": {**run_row, "details": from_json(run_row.get("details_json"), {})},
        "publications": [{**row, "metadata": from_json(row.get("metadata_json"), {})} for row in publications],
    }
