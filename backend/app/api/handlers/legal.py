from __future__ import annotations

from fastapi import HTTPException, Request

from .common import *
from ...legal_assets import LEGAL_OWNER, LEGAL_PRODUCT, PUBLIC_LEGAL_CONTENT, PUBLIC_LEGAL_DOCS, SUBPROCESSORS_PUBLIC
from ...schemas import CookieConsentUpsertRequest, LegalAcceptanceRequest, PrivacyRightsRequest


def _subject_parts(*, anonymous_id: str | None, organization_id: str | None, contact_id: str | None, user_id: str | None) -> tuple[str, str]:
    if user_id:
        return "user", user_id
    if contact_id:
        return "contact", contact_id
    if organization_id:
        return "organization", organization_id
    if anonymous_id:
        return "anonymous", anonymous_id
    return "anonymous", new_id("anon")


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or None
    return request.client.host if request.client else None


def _record_audit_event(conn, *, event_type: str, subject_type: str | None, subject_key: str | None, payload: dict, request: Request) -> None:
    now = utcnow_iso()
    execute(
        conn,
        """
        INSERT INTO legal_audit_events (
            id, event_type, subject_type, subject_key, actor_type, actor_id, request_id, ip_address, user_agent,
            payload_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("lae"),
            event_type,
            subject_type,
            subject_key,
            "public_request",
            None,
            getattr(request.state, "request_id", None),
            _client_ip(request),
            request.headers.get("user-agent"),
            to_json(payload),
            now,
        ),
    )


def list_public_legal_docs() -> dict:
    categories = sorted({str(item.get("category") or "General") for item in PUBLIC_LEGAL_DOCS})
    return ok({
        "owner": LEGAL_OWNER,
        "product": LEGAL_PRODUCT,
        "count": len(PUBLIC_LEGAL_DOCS),
        "categories": categories,
        "documents": PUBLIC_LEGAL_DOCS,
    })


def get_public_legal_doc(slug: str) -> dict:
    doc = next((item for item in PUBLIC_LEGAL_DOCS if item.get("slug") == slug), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento legal no encontrado")
    content = PUBLIC_LEGAL_CONTENT.get(slug)
    if content is None:
        raise HTTPException(status_code=404, detail="Contenido legal no disponible")
    return ok({**doc, "content": content, "owner": LEGAL_OWNER, "product": LEGAL_PRODUCT})


def get_public_subprocessors() -> dict:
    return ok(SUBPROCESSORS_PUBLIC)


def upsert_cookie_consent(payload: CookieConsentUpsertRequest, request: Request) -> dict:
    normalized = {
        "necessary": bool(payload.categories.get("necessary", True)),
        "analytics": bool(payload.categories.get("analytics", False)),
        "preferences": bool(payload.categories.get("preferences", False)),
        "marketing": bool(payload.categories.get("marketing", False)),
    }
    subject_type, subject_key = _subject_parts(
        anonymous_id=payload.anonymous_id,
        organization_id=payload.organization_id,
        contact_id=payload.contact_id,
        user_id=payload.user_id,
    )
    now = utcnow_iso()
    evidence = {
        "source": payload.source,
        "page_url": payload.page_url,
        "ip_address": _client_ip(request),
        "user_agent": request.headers.get("user-agent"),
        "version": payload.consent_version,
    }
    with get_connection() as conn:
        execute(
            conn,
            """
            INSERT INTO legal_consent_records (
                id, subject_type, subject_key, organization_id, contact_id, user_id,
                consent_key, status, version, categories_json, source, evidence_json, metadata_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(subject_type, subject_key, consent_key)
            DO UPDATE SET
                organization_id = excluded.organization_id,
                contact_id = excluded.contact_id,
                user_id = excluded.user_id,
                status = excluded.status,
                version = excluded.version,
                categories_json = excluded.categories_json,
                source = excluded.source,
                evidence_json = excluded.evidence_json,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
            """,
            (
                new_id("lcr"),
                subject_type,
                subject_key,
                payload.organization_id,
                payload.contact_id,
                payload.user_id,
                "cookies",
                "granted" if any(value for key, value in normalized.items() if key != "necessary") else "essential_only",
                payload.consent_version,
                to_json(normalized),
                payload.source,
                to_json(evidence),
                to_json(payload.metadata),
                now,
                now,
            ),
        )
        _record_audit_event(conn, event_type="cookie_consent_updated", subject_type=subject_type, subject_key=subject_key, payload={"categories": normalized, "version": payload.consent_version, "source": payload.source}, request=request)
    return ok({"subject_type": subject_type, "subject_key": subject_key, "consent_key": "cookies", "categories": normalized, "version": payload.consent_version, "updated_at": now})


def record_legal_acceptance(payload: LegalAcceptanceRequest, request: Request) -> dict:
    doc = next((item for item in PUBLIC_LEGAL_DOCS if item.get("slug") == payload.slug), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento legal no encontrado")
    subject_type, subject_key = _subject_parts(
        anonymous_id=payload.anonymous_id,
        organization_id=payload.organization_id,
        contact_id=payload.contact_id,
        user_id=payload.user_id,
    )
    now = utcnow_iso()
    evidence = {
        "source": payload.source,
        "page_url": payload.page_url,
        "ip_address": _client_ip(request),
        "user_agent": request.headers.get("user-agent"),
    }
    with get_connection() as conn:
        execute(
            conn,
            """
            INSERT INTO legal_acceptance_events (
                id, slug, version, acceptance_type, subject_type, subject_key,
                organization_id, contact_id, user_id, source, evidence_json, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("laa"),
                payload.slug,
                payload.version,
                payload.acceptance_type,
                subject_type,
                subject_key,
                payload.organization_id,
                payload.contact_id,
                payload.user_id,
                payload.source,
                to_json(evidence),
                to_json(payload.metadata),
                now,
            ),
        )
        _record_audit_event(conn, event_type="legal_document_accepted", subject_type=subject_type, subject_key=subject_key, payload={"slug": payload.slug, "version": payload.version, "acceptance_type": payload.acceptance_type}, request=request)
    return ok({"slug": payload.slug, "version": payload.version, "subject_type": subject_type, "subject_key": subject_key, "accepted_at": now, "title": doc.get("title")})


def create_privacy_rights_request(payload: PrivacyRightsRequest, request: Request) -> dict:
    now = utcnow_iso()
    subject_key = payload.email or payload.phone or payload.contact_id or new_id("privacy")
    with get_connection() as conn:
        request_id = new_id("prv")
        execute(
            conn,
            """
            INSERT INTO privacy_requests (
                id, request_type, status, requester_name, email, phone,
                organization_id, contact_id, country, message, source, metadata_json,
                requested_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                payload.request_type,
                "received",
                payload.name,
                payload.email,
                payload.phone,
                payload.organization_id,
                payload.contact_id,
                payload.country,
                payload.message,
                payload.source,
                to_json({**payload.metadata, "ip_address": _client_ip(request), "user_agent": request.headers.get("user-agent")}),
                now,
                now,
            ),
        )
        _record_audit_event(conn, event_type="privacy_request_created", subject_type="privacy_request", subject_key=request_id, payload={"request_type": payload.request_type, "email": payload.email, "phone": payload.phone, "source": payload.source}, request=request)
    return ok({"id": request_id, "status": "received", "requested_at": now, "request_type": payload.request_type, "reference": subject_key})
