from __future__ import annotations

from typing import Any

from .domains.bot_behavior import upsert_bot_behavior_settings, upsert_bot_response_template
from .domains.catalog import create_catalog_service
from .knowledge_runtime import ingest_knowledge_document
from .utils import from_json, new_id, slugify, to_json, utcnow_iso
from .world_class import execute, fetch_all, fetch_one, table_exists

VERTICAL_MARKETPLACE_VERSION = "vertical_marketplace_v1"
_ALLOWED_PACKAGE_TYPES = {"vertical", "playbook", "onboarding_pack", "prompt_pack", "automation_pack"}


def ensure_vertical_marketplace_schema(conn: Any) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS vertical_marketplace_packages (
            id TEXT PRIMARY KEY,
            package_slug TEXT NOT NULL UNIQUE,
            package_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            vertical_key TEXT,
            subvertical TEXT,
            publisher_type TEXT NOT NULL DEFAULT 'core',
            publisher_user_id TEXT,
            publisher_org_id TEXT,
            monetization_model TEXT NOT NULL DEFAULT 'internal',
            price_amount REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'USD',
            status TEXT NOT NULL DEFAULT 'draft',
            latest_version_id TEXT,
            compatibility_json TEXT NOT NULL DEFAULT '{}',
            dependencies_json TEXT NOT NULL DEFAULT '[]',
            metrics_expected_json TEXT NOT NULL DEFAULT '{}',
            manifest_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (publisher_user_id) REFERENCES users(id),
            FOREIGN KEY (publisher_org_id) REFERENCES organizations(id)
        );
        CREATE INDEX IF NOT EXISTS idx_vertical_marketplace_packages_type ON vertical_marketplace_packages(package_type, status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_vertical_marketplace_packages_vertical ON vertical_marketplace_packages(vertical_key, subvertical, status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS vertical_marketplace_package_versions (
            id TEXT PRIMARY KEY,
            package_id TEXT NOT NULL,
            version TEXT NOT NULL,
            release_notes TEXT,
            status TEXT NOT NULL DEFAULT 'published',
            bundle_json TEXT NOT NULL DEFAULT '{}',
            compatibility_json TEXT NOT NULL DEFAULT '{}',
            dependencies_json TEXT NOT NULL DEFAULT '[]',
            checklist_json TEXT NOT NULL DEFAULT '[]',
            metrics_expected_json TEXT NOT NULL DEFAULT '{}',
            published_at TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT,
            UNIQUE(package_id, version),
            FOREIGN KEY (package_id) REFERENCES vertical_marketplace_packages(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_vertical_marketplace_package_versions_pkg ON vertical_marketplace_package_versions(package_id, published_at DESC, created_at DESC);

        CREATE TABLE IF NOT EXISTS vertical_marketplace_installs (
            id TEXT PRIMARY KEY,
            package_id TEXT NOT NULL,
            package_version_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            install_scope TEXT NOT NULL DEFAULT 'organization',
            status TEXT NOT NULL DEFAULT 'installed',
            compatibility_snapshot_json TEXT NOT NULL DEFAULT '{}',
            installed_manifest_json TEXT NOT NULL DEFAULT '{}',
            install_summary_json TEXT NOT NULL DEFAULT '{}',
            current_version TEXT NOT NULL,
            source_channel TEXT NOT NULL DEFAULT 'marketplace',
            upgrade_available INTEGER NOT NULL DEFAULT 0,
            installed_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            installed_by TEXT,
            FOREIGN KEY (package_id) REFERENCES vertical_marketplace_packages(id),
            FOREIGN KEY (package_version_id) REFERENCES vertical_marketplace_package_versions(id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (installed_by) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_vertical_marketplace_installs_org ON vertical_marketplace_installs(organization_id, status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_vertical_marketplace_installs_pkg ON vertical_marketplace_installs(package_id, current_version, updated_at DESC);

        CREATE TABLE IF NOT EXISTS vertical_marketplace_install_items (
            id TEXT PRIMARY KEY,
            install_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            item_type TEXT NOT NULL,
            item_key TEXT NOT NULL,
            entity_id TEXT,
            status TEXT NOT NULL DEFAULT 'installed',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (install_id) REFERENCES vertical_marketplace_installs(id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id)
        );
        CREATE INDEX IF NOT EXISTS idx_vertical_marketplace_install_items_install ON vertical_marketplace_install_items(install_id, item_type, created_at DESC);

        CREATE TABLE IF NOT EXISTS vertical_marketplace_upgrade_runs (
            id TEXT PRIMARY KEY,
            install_id TEXT NOT NULL,
            package_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            bot_id TEXT,
            from_version TEXT NOT NULL,
            to_version TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned',
            plan_json TEXT NOT NULL DEFAULT '{}',
            result_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            executed_at TEXT,
            executed_by TEXT,
            FOREIGN KEY (install_id) REFERENCES vertical_marketplace_installs(id),
            FOREIGN KEY (package_id) REFERENCES vertical_marketplace_packages(id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (bot_id) REFERENCES bots(id),
            FOREIGN KEY (executed_by) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_vertical_marketplace_upgrade_runs_install ON vertical_marketplace_upgrade_runs(install_id, created_at DESC);
        """
    )


def _normalize_package_type(value: str | None) -> str:
    token = str(value or "vertical").strip().lower()
    return token if token in _ALLOWED_PACKAGE_TYPES else "vertical"


def _parse_semver(value: str | None) -> tuple[int, int, int, str]:
    raw = str(value or "0.0.0").strip()
    base, _, suffix = raw.partition("-")
    parts = [part for part in base.split(".") if part != ""]
    ints = []
    for idx in range(3):
        try:
            ints.append(int(parts[idx]))
        except Exception:
            ints.append(0)
    return ints[0], ints[1], ints[2], suffix


def _version_greater(left: str | None, right: str | None) -> bool:
    return _parse_semver(left) > _parse_semver(right)


def _parse_json_fields(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return row
    parsed = dict(row)
    for key, default in {
        "compatibility_json": {},
        "dependencies_json": [],
        "metrics_expected_json": {},
        "manifest_json": {},
        "metadata_json": {},
        "bundle_json": {},
        "checklist_json": [],
        "compatibility_snapshot_json": {},
        "installed_manifest_json": {},
        "install_summary_json": {},
        "plan_json": {},
        "result_json": {},
    }.items():
        if key in parsed:
            parsed[key[:-5]] = from_json(parsed.get(key), default)
    return parsed


def _sorted_versions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(((_parse_json_fields(row) or row) for row in rows), key=lambda item: (_parse_semver(item.get("version")), item.get("published_at") or item.get("created_at") or ""), reverse=True)


def _latest_version(conn: Any, package_id: str) -> dict[str, Any] | None:
    rows = fetch_all(conn, "SELECT * FROM vertical_marketplace_package_versions WHERE package_id = ?", (package_id,))
    versions = _sorted_versions(rows)
    return versions[0] if versions else None


def list_marketplace_packages(
    conn: Any,
    *,
    vertical_key: str | None = None,
    package_type: str | None = None,
    status: str | None = "published",
    limit: int = 100,
) -> list[dict[str, Any]]:
    ensure_vertical_marketplace_schema(conn)
    sql = "SELECT * FROM vertical_marketplace_packages WHERE 1 = 1"
    params: list[Any] = []
    if vertical_key:
        sql += " AND (vertical_key = ? OR vertical_key IS NULL OR vertical_key = '')"
        params.append(vertical_key)
    if package_type:
        sql += " AND package_type = ?"
        params.append(_normalize_package_type(package_type))
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(max(1, min(limit, 500)))
    rows = [_parse_json_fields(row) for row in fetch_all(conn, sql, params)]
    items: list[dict[str, Any]] = []
    for row in rows:
        latest = _latest_version(conn, row["id"])
        payload = dict(row)
        payload["latest_version"] = latest
        items.append(payload)
    return items


def get_marketplace_package(conn: Any, package_id: str) -> dict[str, Any] | None:
    ensure_vertical_marketplace_schema(conn)
    row = fetch_one(conn, "SELECT * FROM vertical_marketplace_packages WHERE id = ?", (package_id,))
    if not row:
        return None
    parsed = _parse_json_fields(row) or {}
    versions = _sorted_versions(fetch_all(conn, "SELECT * FROM vertical_marketplace_package_versions WHERE package_id = ?", (package_id,)))
    installs = fetch_one(conn, "SELECT COUNT(*) AS count FROM vertical_marketplace_installs WHERE package_id = ?", (package_id,)) or {"count": 0}
    parsed["versions"] = versions
    parsed["latest_version"] = versions[0] if versions else None
    parsed["installs_count"] = int(installs.get("count") or 0)
    return parsed


def publish_marketplace_package(
    conn: Any,
    *,
    package_type: str,
    package_slug: str,
    title: str,
    summary: str,
    version: str,
    manifest: dict[str, Any] | None,
    vertical_key: str | None = None,
    subvertical: str | None = None,
    compatibility: dict[str, Any] | None = None,
    dependencies: list[dict[str, Any]] | list[str] | None = None,
    checklist: list[dict[str, Any]] | list[str] | None = None,
    metrics_expected: dict[str, Any] | None = None,
    monetization_model: str = "internal",
    price_amount: float | int | None = None,
    currency: str = "USD",
    publisher_user_id: str | None = None,
    publisher_org_id: str | None = None,
    release_notes: str | None = None,
    metadata: dict[str, Any] | None = None,
    status: str = "published",
) -> dict[str, Any]:
    ensure_vertical_marketplace_schema(conn)
    now = utcnow_iso()
    package_type = _normalize_package_type(package_type)
    package_slug = slugify(package_slug or title or package_type)
    if not package_slug:
        raise ValueError("package_slug is required")
    version = str(version or "1.0.0").strip() or "1.0.0"
    manifest = manifest or {}
    compatibility = compatibility or {}
    dependencies = list(dependencies or [])
    checklist = list(checklist or [])
    metrics_expected = metrics_expected or {}
    metadata = metadata or {}
    existing = fetch_one(conn, "SELECT * FROM vertical_marketplace_packages WHERE package_slug = ?", (package_slug,))
    package_id = existing["id"] if existing else new_id("vmpkg")
    if existing:
        execute(
            conn,
            """
            UPDATE vertical_marketplace_packages
            SET package_type = ?, title = ?, summary = ?, vertical_key = ?, subvertical = ?, publisher_type = ?, publisher_user_id = ?, publisher_org_id = ?, monetization_model = ?, price_amount = ?, currency = ?, status = ?, compatibility_json = ?, dependencies_json = ?, metrics_expected_json = ?, manifest_json = ?, metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                package_type, title, summary, vertical_key, subvertical, metadata.get("publisher_type") or (existing.get("publisher_type") if existing else "core"), publisher_user_id, publisher_org_id, monetization_model, float(price_amount or 0), currency, status, to_json(compatibility), to_json(dependencies), to_json(metrics_expected), to_json(manifest), to_json(metadata), now, package_id,
            ),
        )
    else:
        execute(
            conn,
            """
            INSERT INTO vertical_marketplace_packages (
                id, package_slug, package_type, title, summary, vertical_key, subvertical, publisher_type, publisher_user_id, publisher_org_id, monetization_model, price_amount, currency, status, latest_version_id, compatibility_json, dependencies_json, metrics_expected_json, manifest_json, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                package_id, package_slug, package_type, title, summary, vertical_key, subvertical, metadata.get("publisher_type") or "core", publisher_user_id, publisher_org_id, monetization_model, float(price_amount or 0), currency, status, to_json(compatibility), to_json(dependencies), to_json(metrics_expected), to_json(manifest), to_json(metadata), now, now,
            ),
        )
    existing_version = fetch_one(conn, "SELECT * FROM vertical_marketplace_package_versions WHERE package_id = ? AND version = ?", (package_id, version))
    version_id = existing_version["id"] if existing_version else new_id("vmpkgv")
    bundle = {
        "manifest": manifest,
        "checklist": checklist,
        "package_slug": package_slug,
        "package_type": package_type,
        "title": title,
        "summary": summary,
        "vertical_key": vertical_key,
        "subvertical": subvertical,
        "release_notes": release_notes,
    }
    if existing_version:
        execute(
            conn,
            "UPDATE vertical_marketplace_package_versions SET release_notes = ?, status = ?, bundle_json = ?, compatibility_json = ?, dependencies_json = ?, checklist_json = ?, metrics_expected_json = ?, published_at = ?, created_by = ? WHERE id = ?",
            (release_notes, status, to_json(bundle), to_json(compatibility), to_json(dependencies), to_json(checklist), to_json(metrics_expected), now, publisher_user_id, version_id),
        )
    else:
        execute(
            conn,
            """
            INSERT INTO vertical_marketplace_package_versions (
                id, package_id, version, release_notes, status, bundle_json, compatibility_json, dependencies_json, checklist_json, metrics_expected_json, published_at, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (version_id, package_id, version, release_notes, status, to_json(bundle), to_json(compatibility), to_json(dependencies), to_json(checklist), to_json(metrics_expected), now, now, publisher_user_id),
        )
    execute(conn, "UPDATE vertical_marketplace_packages SET latest_version_id = ?, updated_at = ? WHERE id = ?", (version_id, now, package_id))
    execute(conn, "UPDATE vertical_marketplace_installs SET upgrade_available = CASE WHEN current_version <> ? THEN 1 ELSE 0 END, updated_at = ? WHERE package_id = ?", (version, now, package_id))
    return get_marketplace_package(conn, package_id) or {"id": package_id, "latest_version_id": version_id}


def _append_install_item(conn: Any, *, install_id: str, organization_id: str, bot_id: str | None, item_type: str, item_key: str, entity_id: str | None, metadata: dict[str, Any] | None = None) -> None:
    execute(
        conn,
        "INSERT INTO vertical_marketplace_install_items (id, install_id, organization_id, bot_id, item_type, item_key, entity_id, status, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'installed', ?, ?)",
        (new_id("vminstitem"), install_id, organization_id, bot_id, item_type, item_key, entity_id, to_json(metadata or {}), utcnow_iso()),
    )


def _ensure_playbook(conn: Any, *, organization_id: str, vertical_key: str | None, name: str, config: dict[str, Any], status: str = "active") -> str:
    existing = fetch_one(conn, "SELECT * FROM industry_playbooks WHERE organization_id = ? AND name = ?", (organization_id, name))
    now = utcnow_iso()
    if existing:
        execute(conn, "UPDATE industry_playbooks SET industry = ?, status = ?, config_json = ?, updated_at = ? WHERE id = ?", (vertical_key or existing.get("industry") or "general", status, to_json(config), now, existing["id"]))
        return existing["id"]
    row_id = new_id("plb")
    execute(conn, "INSERT INTO industry_playbooks (id, organization_id, industry, name, status, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (row_id, organization_id, vertical_key or "general", name, status, to_json(config), now, now))
    return row_id


def _ensure_automation_rule(conn: Any, *, organization_id: str, bot_id: str, name: str, rule_type: str, status: str, config: dict[str, Any]) -> str:
    existing = fetch_one(conn, "SELECT * FROM automation_rules WHERE organization_id = ? AND bot_id = ? AND name = ? AND rule_type = ?", (organization_id, bot_id, name, rule_type))
    now = utcnow_iso()
    if existing:
        execute(conn, "UPDATE automation_rules SET status = ?, config_json = ?, updated_at = ? WHERE id = ?", (status, to_json(config), now, existing["id"]))
        return existing["id"]
    row_id = new_id("autr")
    execute(conn, "INSERT INTO automation_rules (id, organization_id, bot_id, rule_type, name, status, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (row_id, organization_id, bot_id, rule_type, name, status, to_json(config), now, now))
    return row_id


def _upsert_integration(conn: Any, *, organization_id: str, bot_id: str | None, integration_type: str, provider: str, name: str, status: str, config: dict[str, Any]) -> str:
    existing = fetch_one(conn, "SELECT * FROM integration_connections WHERE organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '') AND integration_type = ? AND provider = ? AND name = ?", (organization_id, bot_id, integration_type, provider, name))
    now = utcnow_iso()
    if existing:
        execute(conn, "UPDATE integration_connections SET status = ?, config_json = ?, updated_at = ? WHERE id = ?", (status, to_json(config), now, existing["id"]))
        return existing["id"]
    row_id = new_id("int")
    execute(conn, "INSERT INTO integration_connections (id, organization_id, bot_id, integration_type, provider, name, status, health_status, credential_status, config_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'unknown', 'pending', ?, ?, ?)", (row_id, organization_id, bot_id, integration_type, provider, name, status, to_json(config), now, now))
    return row_id


def _apply_marketplace_manifest(conn: Any, *, install_id: str, organization_id: str, bot_id: str | None, package: dict[str, Any], package_version: dict[str, Any], actor_user: dict | None) -> dict[str, Any]:
    bundle = package_version.get("bundle") or {}
    manifest = bundle.get("manifest") or package.get("manifest") or {}
    created = {"templates": [], "knowledge_documents": [], "catalog_services": [], "integrations": [], "playbooks": [], "automations": []}
    vertical_key = package.get("vertical_key") or manifest.get("vertical_key")
    if bot_id and manifest.get("behavior"):
        behavior = manifest.get("behavior") or {}
        upsert_bot_behavior_settings(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            tone=str(behavior.get("tone") or "cercano"),
            response_length=str(behavior.get("response_length") or "media"),
            sales_intensity=str(behavior.get("sales_intensity") or "media"),
            offer_promotions_when=str(behavior.get("offer_promotions_when") or "when_relevant"),
            escalate_when=list(behavior.get("escalate_when") or []),
            forbidden_topics=list(behavior.get("forbidden_topics") or []),
            required_phrases=list(behavior.get("required_phrases") or []),
            bot_mode=str(behavior.get("bot_mode") or "hybrid"),
            actor_user=actor_user,
        )
        _append_install_item(conn, install_id=install_id, organization_id=organization_id, bot_id=bot_id, item_type="behavior", item_key="bot_behavior_settings", entity_id=bot_id, metadata=behavior)
    for template in manifest.get("templates") or []:
        if not bot_id:
            continue
        row = upsert_bot_response_template(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            template_key=str(template.get("template_key") or slugify(template.get("title") or "marketplace-template")),
            channel=str(template.get("channel") or "whatsapp"),
            title=template.get("title"),
            content=str(template.get("content") or "").strip(),
            variables=list(template.get("variables") or []),
            actor_user=actor_user,
        )
        created["templates"].append(row.get("template_key"))
        _append_install_item(conn, install_id=install_id, organization_id=organization_id, bot_id=bot_id, item_type="template", item_key=row.get("template_key") or "template", entity_id=row.get("id"), metadata={"channel": row.get("channel")})
    for doc in manifest.get("knowledge_documents") or []:
        if not bot_id:
            continue
        source_key = str(doc.get("source_key") or f"marketplace:{package['package_slug']}:{slugify(doc.get('title') or 'doc')}")
        row = ingest_knowledge_document(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            title=str(doc.get("title") or package.get("title") or "Marketplace knowledge"),
            source_kind=str(doc.get("source_kind") or "import"),
            source_key=source_key,
            content_text=str(doc.get("content_text") or "").strip(),
            domain=str(doc.get("domain") or "support"),
            source_uri=doc.get("source_uri"),
            tags=list(doc.get("tags") or []),
            supports=list(doc.get("supports") or []),
            metadata={**(doc.get("metadata") or {}), "marketplace_package_slug": package.get("package_slug"), "marketplace_version": package_version.get("version")},
            owner_type="marketplace",
        )
        created["knowledge_documents"].append(row.get("source_key"))
        _append_install_item(conn, install_id=install_id, organization_id=organization_id, bot_id=bot_id, item_type="knowledge_document", item_key=row.get("source_key") or source_key, entity_id=row.get("id"), metadata={"title": row.get("title")})
    for service in manifest.get("catalog_services") or []:
        if not bot_id:
            continue
        existing = fetch_one(conn, "SELECT * FROM catalog_services WHERE organization_id = ? AND bot_id = ? AND name = ?", (organization_id, bot_id, service.get("name")))
        if existing:
            service_id = existing["id"]
        else:
            row = create_catalog_service(
                conn,
                organization_id=organization_id,
                bot_id=bot_id,
                name=str(service.get("name") or package.get("title") or "Marketplace service"),
                duration_minutes=int(service.get("duration_minutes") or 30),
                price=float(service.get("price") or 0),
                currency=str(service.get("currency") or "MXN"),
                preparation=str(service.get("preparation") or ""),
                restrictions=str(service.get("restrictions") or ""),
                availability=dict(service.get("availability") or {}),
                status=str(service.get("status") or "active"),
                actor_user=actor_user,
            )
            service_id = row.get("id")
        created["catalog_services"].append(str(service.get("name") or service_id))
        _append_install_item(conn, install_id=install_id, organization_id=organization_id, bot_id=bot_id, item_type="catalog_service", item_key=str(service.get("name") or service_id), entity_id=service_id, metadata={"price": service.get("price")})
    for integration in manifest.get("integrations") or []:
        entity_id = _upsert_integration(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            integration_type=str(integration.get("integration_type") or "knowledge"),
            provider=str(integration.get("provider") or "unknown"),
            name=str(integration.get("name") or integration.get("provider") or "integration"),
            status=str(integration.get("status") or "planned"),
            config=dict(integration.get("config") or {}),
        )
        created["integrations"].append(str(integration.get("provider") or entity_id))
        _append_install_item(conn, install_id=install_id, organization_id=organization_id, bot_id=bot_id, item_type="integration", item_key=str(integration.get("provider") or entity_id), entity_id=entity_id, metadata={"integration_type": integration.get("integration_type")})
    for playbook in manifest.get("playbooks") or []:
        playbook_id = _ensure_playbook(
            conn,
            organization_id=organization_id,
            vertical_key=vertical_key,
            name=str(playbook.get("name") or package.get("title") or "Marketplace playbook"),
            config=dict(playbook.get("config") or {}),
            status=str(playbook.get("status") or "active"),
        )
        created["playbooks"].append(str(playbook.get("name") or playbook_id))
        _append_install_item(conn, install_id=install_id, organization_id=organization_id, bot_id=bot_id, item_type="playbook", item_key=str(playbook.get("name") or playbook_id), entity_id=playbook_id, metadata=playbook.get("config") or {})
    for automation in manifest.get("automations") or []:
        if not bot_id:
            continue
        automation_id = _ensure_automation_rule(
            conn,
            organization_id=organization_id,
            bot_id=bot_id,
            name=str(automation.get("name") or package.get("title") or "Marketplace automation"),
            rule_type=str(automation.get("rule_type") or "followup"),
            status=str(automation.get("status") or "active"),
            config=dict(automation.get("config") or {}),
        )
        created["automations"].append(str(automation.get("name") or automation_id))
        _append_install_item(conn, install_id=install_id, organization_id=organization_id, bot_id=bot_id, item_type="automation", item_key=str(automation.get("name") or automation_id), entity_id=automation_id, metadata=automation.get("config") or {})
    package_ref = {
        "package_id": package.get("id"),
        "package_slug": package.get("package_slug"),
        "title": package.get("title"),
        "current_version": package_version.get("version"),
        "package_type": package.get("package_type"),
        "vertical_key": vertical_key,
    }
    org = fetch_one(conn, "SELECT settings_json FROM organizations WHERE id = ?", (organization_id,)) or {"settings_json": "{}"}
    org_settings = from_json(org.get("settings_json"), {})
    marketplace_state = org_settings.setdefault("vertical_marketplace", {})
    installed = list(marketplace_state.get("installed_packages") or [])
    installed = [item for item in installed if item.get("package_id") != package_ref["package_id"]]
    installed.append(package_ref)
    marketplace_state["installed_packages"] = installed
    marketplace_state["last_install"] = package_ref
    execute(conn, "UPDATE organizations SET settings_json = ?, updated_at = ? WHERE id = ?", (to_json(org_settings), utcnow_iso(), organization_id))
    if bot_id:
        bot = fetch_one(conn, "SELECT config_draft_json FROM bots WHERE id = ?", (bot_id,)) or {"config_draft_json": "{}"}
        bot_config = from_json(bot.get("config_draft_json"), {})
        bot_marketplace = bot_config.setdefault("vertical_marketplace", {})
        bot_packages = list(bot_marketplace.get("installed_packages") or [])
        bot_packages = [item for item in bot_packages if item.get("package_id") != package_ref["package_id"]]
        bot_packages.append(package_ref)
        bot_marketplace["installed_packages"] = bot_packages
        bot_marketplace["last_install"] = package_ref
        if vertical_key:
            bot_config["marketplace_vertical"] = vertical_key
        execute(conn, "UPDATE bots SET config_draft_json = ?, updated_at = ? WHERE id = ?", (to_json(bot_config), utcnow_iso(), bot_id))
    return created


def _resolve_package_version(conn: Any, *, package_id: str | None = None, package_slug: str | None = None, version: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    package = None
    if package_id:
        package = fetch_one(conn, "SELECT * FROM vertical_marketplace_packages WHERE id = ?", (package_id,))
    elif package_slug:
        package = fetch_one(conn, "SELECT * FROM vertical_marketplace_packages WHERE package_slug = ?", (slugify(package_slug),))
    if not package:
        raise ValueError("package_not_found")
    package = _parse_json_fields(package) or package
    if version:
        package_version = fetch_one(conn, "SELECT * FROM vertical_marketplace_package_versions WHERE package_id = ? AND version = ?", (package["id"], version))
    else:
        package_version = _latest_version(conn, package["id"])
    if not package_version:
        raise ValueError("package_version_not_found")
    return package, _parse_json_fields(package_version) or package_version


def install_marketplace_package(
    conn: Any,
    *,
    organization_id: str,
    bot_id: str | None,
    actor_user: dict | None,
    package_id: str | None = None,
    package_slug: str | None = None,
    version: str | None = None,
    install_scope: str = "organization",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_vertical_marketplace_schema(conn)
    package, package_version = _resolve_package_version(conn, package_id=package_id, package_slug=package_slug, version=version)
    existing = fetch_one(conn, "SELECT * FROM vertical_marketplace_installs WHERE package_id = ? AND organization_id = ? AND COALESCE(bot_id,'') = COALESCE(?, '')", (package["id"], organization_id, bot_id))
    if existing and not _version_greater(package_version.get("version"), existing.get("current_version")):
        existing_payload = _parse_json_fields(existing) or existing
        existing_payload["package"] = package
        existing_payload["package_version"] = package_version
        return existing_payload
    now = utcnow_iso()
    install_id = existing["id"] if existing else new_id("vminst")
    if existing:
        execute(conn, "UPDATE vertical_marketplace_installs SET status = 'installing', updated_at = ? WHERE id = ?", (now, install_id))
    else:
        execute(conn, "INSERT INTO vertical_marketplace_installs (id, package_id, package_version_id, organization_id, bot_id, install_scope, status, compatibility_snapshot_json, installed_manifest_json, install_summary_json, current_version, source_channel, upgrade_available, installed_at, updated_at, installed_by) VALUES (?, ?, ?, ?, ?, ?, 'installing', '{}', '{}', '{}', ?, 'marketplace', 0, ?, ?, ?)", (install_id, package["id"], package_version["id"], organization_id, bot_id, install_scope, package_version.get("version"), now, now, actor_user.get("id") if actor_user else None))
    created = _apply_marketplace_manifest(conn, install_id=install_id, organization_id=organization_id, bot_id=bot_id, package=package, package_version=package_version, actor_user=actor_user)
    summary = {
        "templates": len(created["templates"]),
        "knowledge_documents": len(created["knowledge_documents"]),
        "catalog_services": len(created["catalog_services"]),
        "integrations": len(created["integrations"]),
        "playbooks": len(created["playbooks"]),
        "automations": len(created["automations"]),
        "created": created,
        "metadata": metadata or {},
    }
    execute(conn, "UPDATE vertical_marketplace_installs SET package_version_id = ?, install_scope = ?, status = 'installed', compatibility_snapshot_json = ?, installed_manifest_json = ?, install_summary_json = ?, current_version = ?, upgrade_available = 0, updated_at = ?, installed_by = ? WHERE id = ?", (package_version["id"], install_scope, to_json(package_version.get("compatibility") or {}), to_json(package_version.get("bundle") or {}), to_json(summary), package_version.get("version"), now, actor_user.get("id") if actor_user else None, install_id))
    install = fetch_one(conn, "SELECT * FROM vertical_marketplace_installs WHERE id = ?", (install_id,))
    payload = _parse_json_fields(install) or {"id": install_id}
    payload["package"] = package
    payload["package_version"] = package_version
    return payload


def list_marketplace_installs(conn: Any, *, organization_id: str, bot_id: str | None = None, package_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    ensure_vertical_marketplace_schema(conn)
    sql = "SELECT * FROM vertical_marketplace_installs WHERE organization_id = ?"
    params: list[Any] = [organization_id]
    if bot_id is not None:
        sql += " AND COALESCE(bot_id,'') = COALESCE(?, '')"
        params.append(bot_id)
    if package_id:
        sql += " AND package_id = ?"
        params.append(package_id)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(max(1, min(limit, 500)))
    items = []
    for row in fetch_all(conn, sql, params):
        parsed = _parse_json_fields(row) or row
        package = fetch_one(conn, "SELECT * FROM vertical_marketplace_packages WHERE id = ?", (parsed["package_id"],))
        version = fetch_one(conn, "SELECT * FROM vertical_marketplace_package_versions WHERE id = ?", (parsed["package_version_id"],))
        parsed["package"] = _parse_json_fields(package)
        parsed["package_version"] = _parse_json_fields(version)
        items.append(parsed)
    return items


def upgrade_marketplace_install(conn: Any, *, install_id: str, actor_user: dict | None, target_version: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_vertical_marketplace_schema(conn)
    install = fetch_one(conn, "SELECT * FROM vertical_marketplace_installs WHERE id = ?", (install_id,))
    if not install:
        raise ValueError("install_not_found")
    install = _parse_json_fields(install) or install
    package = fetch_one(conn, "SELECT * FROM vertical_marketplace_packages WHERE id = ?", (install["package_id"],))
    if not package:
        raise ValueError("package_not_found")
    package = _parse_json_fields(package) or package
    _, package_version = _resolve_package_version(conn, package_id=package["id"], version=target_version)
    if not _version_greater(package_version.get("version"), install.get("current_version")):
        raise ValueError("no_upgrade_available")
    upgrade_id = new_id("vmup")
    plan = {
        "package_slug": package.get("package_slug"),
        "from_version": install.get("current_version"),
        "to_version": package_version.get("version"),
        "metadata": metadata or {},
    }
    execute(conn, "INSERT INTO vertical_marketplace_upgrade_runs (id, install_id, package_id, organization_id, bot_id, from_version, to_version, status, plan_json, result_json, created_at, executed_at, executed_by) VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, '{}', ?, NULL, ?)", (upgrade_id, install_id, package["id"], install["organization_id"], install.get("bot_id"), install.get("current_version"), package_version.get("version"), to_json(plan), utcnow_iso(), actor_user.get("id") if actor_user else None))
    upgraded = install_marketplace_package(
        conn,
        organization_id=install["organization_id"],
        bot_id=install.get("bot_id"),
        actor_user=actor_user,
        package_id=package["id"],
        version=package_version.get("version"),
        install_scope=install.get("install_scope") or "organization",
        metadata=metadata,
    )
    execute(conn, "UPDATE vertical_marketplace_upgrade_runs SET status = 'completed', result_json = ?, executed_at = ? WHERE id = ?", (to_json({"install_id": upgraded.get("id"), "current_version": upgraded.get("current_version")}), utcnow_iso(), upgrade_id))
    upgraded["upgrade_run"] = _parse_json_fields(fetch_one(conn, "SELECT * FROM vertical_marketplace_upgrade_runs WHERE id = ?", (upgrade_id,)))
    return upgraded
