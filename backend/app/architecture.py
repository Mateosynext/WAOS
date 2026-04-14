from __future__ import annotations

"""Authoritative architecture boundaries for the active backend."""

ARCHITECTURE_SOURCES_OF_TRUTH = {
    "transactional_motor": "backend.app.vertical_transactions",
    "vertical_domain_runtime": "backend.app.vertical_domain_runtime",
    "integrations_runtime": "backend.app.integrations_runtime",
    "api_entrypoint": "backend.app.main",
}

DEPRECATED_NAMESPACE = "backend.app.legacy"

ACTIVE_BOUNDARIES = {
    "api": "backend.app.api",
    "application": "backend.app.application",
    "domains": "backend.app.domains",
    "platform": "backend.app.platform",
    "providers": "backend.app.providers",
    "repositories": "backend.app.repositories",
    "schemas": "backend.app.schemas",
    "services": "backend.app.services",
}
