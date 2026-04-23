from __future__ import annotations

"""Authoritative architecture boundaries for the active backend."""

ARCHITECTURE_SOURCES_OF_TRUTH = {
    "transactional_motor": "backend.app.vertical_transactions",
    "vertical_domain_runtime": "backend.app.vertical_domain_runtime",
    "integrations_runtime": "backend.app.integrations_runtime",
    "api_entrypoint": "backend.app.main",
    "canonical_inbound_service": "backend.app.application.inbound_service",
    "runtime_pipeline": "backend.app.runtime_pipeline",
    "agent_runtime": "backend.app.agent_runtime",
    "policy_engine": "backend.app.policy_engine",
}

DEPRECATED_NAMESPACE = "backend.app.legacy"
DEPRECATED_ROOT_MODULES = ["backend.app.v7", "backend.app.v8", "backend.app.v9", "backend.app.platform_legacy", "backend.app.repositories_legacy", "backend.app.schemas_legacy"]

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

CANONICAL_REQUEST_FLOW = [
    "api.router -> application service",
    "application service -> repositories/platform/providers",
    "application service -> runtime pipeline (understand / plan / ground / decide / render / verify / schedule)",
    "platform + providers -> external systems",
]


PLATFORM_OWNERSHIP = {
    "platform_runtime": "backend.app.platform.runtime",
    "platform_security": "backend.app.platform.security",
    "platform_observability": "backend.app.platform.observability",
    "http_security_boundary": "backend.app.security",
}

ROOT_ACTIVE_EXCEPTIONS = [
    "backend.app.main",
    "backend.app.config",
    "backend.app.security",
    "backend.app.observability",
]
