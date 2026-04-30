from __future__ import annotations

import os
import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse


DEFAULT_PUBLIC_APP_URL = "https://app.example.com"
DEFAULT_API_BASE_URL = "https://api.example.com"
DEFAULT_API_INTERNAL_URL = "http://backend:8000"
DEFAULT_CORS_ALLOWED_ORIGINS = DEFAULT_PUBLIC_APP_URL
DEFAULT_ALLOWED_HOSTS = "app.example.com,api.example.com"
DEFAULT_SECRET_SENTINELS = {"", "waos-dev-secret-key", "changeme", "change_me", "replace_me", "example", "default"}
DEFAULT_META_VERIFY_SENTINELS = {"", "changeme", "change_me", "replace_me", "example", "default"}
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
OPENAI_API_BASE_URL = "https://api.openai.com/v1"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "WAOS")
    app_env: str = os.getenv("APP_ENV", "development")
    app_version: str = os.getenv("APP_VERSION", "0.17.5")
    app_secret: str = os.getenv("APP_SECRET", "waos-dev-secret-key")
    secret_encryption_key: str = os.getenv("SECRET_ENCRYPTION_KEY", os.getenv("APP_SECRET", "waos-dev-secret-key"))
    database_url: str = os.getenv("DATABASE_URL", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", OPENAI_API_BASE_URL)
    openai_timeout_seconds: int = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
    autopilot_max_autofix_rounds: int = int(os.getenv("AUTOPILOT_MAX_AUTOFIX_ROUNDS", "2"))
    ai_enable_godmode: bool = _env_bool("AI_ENABLE_GODMODE", False)
    ai_enable_workflow_engine: bool = _env_bool("AI_ENABLE_WORKFLOW_ENGINE", True)
    ai_enable_bot_autopilot_v2: bool = _env_bool("AI_ENABLE_BOT_AUTOPILOT_V2", True)
    ai_enable_simulation_suite: bool = _env_bool("AI_ENABLE_SIMULATION_SUITE", True)
    ai_enable_go_live_readiness: bool = _env_bool("AI_ENABLE_GO_LIVE_READINESS", True)
    ai_enable_ai_command_center: bool = _env_bool("AI_ENABLE_AI_COMMAND_CENTER", True)
    ai_enable_ai_ops_inspector: bool = _env_bool("AI_ENABLE_AI_OPS_INSPECTOR", False)
    ai_enable_proactive_reasoning: bool = _env_bool("AI_ENABLE_PROACTIVE_REASONING", True)
    ai_enable_outcomes_learning: bool = _env_bool("AI_ENABLE_OUTCOMES_LEARNING", True)
    ai_max_cost_per_run: float = float(os.getenv("AI_MAX_COST_PER_RUN", "12"))
    ai_provider_timeout_ms: int = int(os.getenv("AI_PROVIDER_TIMEOUT_MS", "30000"))
    ai_workflow_recovery_on_startup: bool = _env_bool("AI_WORKFLOW_RECOVERY_ON_STARTUP", True)
    ai_workflow_recovery_stale_after_minutes: int = int(os.getenv("AI_WORKFLOW_RECOVERY_STALE_AFTER_MINUTES", "30"))
    meta_graph_api_base: str = os.getenv("META_GRAPH_API_BASE", "https://graph.facebook.com/v23.0")
    meta_verify_token: str = os.getenv("META_VERIFY_TOKEN", "")
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "America/Mexico_City")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    sentry_dsn: str = os.getenv("SENTRY_DSN", "")
    otel_export_enabled: bool = _env_bool("OTEL_EXPORT_ENABLED", False)
    otel_export_endpoint: str = os.getenv("OTEL_EXPORT_ENDPOINT", "")
    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "waos-api")
    otel_export_timeout_seconds: int = int(os.getenv("OTEL_EXPORT_TIMEOUT_SECONDS", "5"))
    datadog_otlp_endpoint: str = os.getenv("DATADOG_OTLP_ENDPOINT", "")
    datadog_api_key_present: bool = bool(os.getenv("DATADOG_API_KEY", "").strip())
    new_relic_otlp_endpoint: str = os.getenv("NEW_RELIC_OTLP_ENDPOINT", "")
    new_relic_license_key_present: bool = bool(os.getenv("NEW_RELIC_LICENSE_KEY", "").strip())
    cors_allowed_origins_raw: str = os.getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ALLOWED_ORIGINS)
    cors_allowed_origin_regex_raw: str = os.getenv("CORS_ALLOWED_ORIGIN_REGEX", "")
    allowed_hosts_raw: str = os.getenv("ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS)
    public_app_url: str = os.getenv("PUBLIC_APP_URL", DEFAULT_PUBLIC_APP_URL)
    api_base_url: str = os.getenv("API_BASE_URL", DEFAULT_API_BASE_URL)
    api_internal_url: str = os.getenv("API_INTERNAL_URL", os.getenv("API_BASE_URL", DEFAULT_API_INTERNAL_URL))
    run_bootstrap_seed: bool = _env_bool("RUN_BOOTSTRAP_SEED", False)
    auto_run_migrations: bool = _env_bool("AUTO_RUN_MIGRATIONS", False)
    db_pool_min_size: int = int(os.getenv("DB_POOL_MIN_SIZE", "4"))
    db_pool_max_size: int = int(os.getenv("DB_POOL_MAX_SIZE", "20"))
    db_pool_timeout_seconds: int = int(os.getenv("DB_POOL_TIMEOUT_SECONDS", "15"))
    max_page_size: int = int(os.getenv("MAX_PAGE_SIZE", "100"))
    default_page_size: int = int(os.getenv("DEFAULT_PAGE_SIZE", "30"))
    runtime_cache_ttl_seconds: int = int(os.getenv("RUNTIME_CACHE_TTL_SECONDS", "10"))
    gzip_minimum_size: int = int(os.getenv("GZIP_MINIMUM_SIZE", "1024"))
    web_concurrency: int = int(os.getenv("WEB_CONCURRENCY", "3" if os.getenv("APP_ENV", "development").strip().lower() == "production" else "2"))
    worker_batch_size: int = int(os.getenv("WORKER_BATCH_SIZE", "50"))
    access_token_ttl_minutes: int = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "60"))
    refresh_token_ttl_minutes: int = int(os.getenv("REFRESH_TOKEN_TTL_MINUTES", "720"))
    session_idle_timeout_minutes: int = int(os.getenv("SESSION_IDLE_TIMEOUT_MINUTES", "120"))
    step_up_window_minutes: int = int(os.getenv("STEP_UP_WINDOW_MINUTES", "15"))
    max_sessions_per_user: int = int(os.getenv("MAX_SESSIONS_PER_USER", "5"))
    login_rate_limit_window_seconds: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900"))
    login_rate_limit_max_attempts: int = int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5"))
    trusted_proxy_ips_raw: str = os.getenv("TRUSTED_PROXY_IPS", "")
    security_hardening_enabled: bool = _env_bool("SECURITY_HARDENING_ENABLED", True)
    enforce_https: bool = _env_bool("ENFORCE_HTTPS", os.getenv("APP_ENV", "development").strip().lower() == "production")
    reject_untrusted_proxy_headers: bool = _env_bool("REJECT_UNTRUSTED_PROXY_HEADERS", os.getenv("APP_ENV", "development").strip().lower() == "production")
    require_signed_webhooks: bool = _env_bool("REQUIRE_SIGNED_WEBHOOKS", os.getenv("APP_ENV", "development").strip().lower() == "production")
    security_rate_limit_enabled: bool = _env_bool("SECURITY_RATE_LIMIT_ENABLED", True)
    rate_limit_backend: str = os.getenv("RATE_LIMIT_BACKEND", "memory").strip().lower()
    rate_limit_redis_url: str = os.getenv("RATE_LIMIT_REDIS_URL", os.getenv("REDIS_URL", "")).strip()
    rate_limit_redis_timeout_seconds: float = float(os.getenv("RATE_LIMIT_REDIS_TIMEOUT_SECONDS", "0.5"))
    rate_limit_key_prefix: str = os.getenv("RATE_LIMIT_KEY_PREFIX", "waos:rate-limit").strip()
    rate_limit_memory_max_buckets: int = int(os.getenv("RATE_LIMIT_MEMORY_MAX_BUCKETS", "10000"))
    rate_limit_memory_eviction_batch: int = int(os.getenv("RATE_LIMIT_MEMORY_EVICTION_BATCH", "128"))
    rate_limit_gateway_enforced: bool = _env_bool("RATE_LIMIT_GATEWAY_ENFORCED", False)
    rate_limit_gateway_fallback_enabled: bool = _env_bool("RATE_LIMIT_GATEWAY_FALLBACK_ENABLED", True)
    global_rate_limit_window_seconds: int = int(os.getenv("GLOBAL_RATE_LIMIT_WINDOW_SECONDS", "60"))
    global_rate_limit_max_requests: int = int(os.getenv("GLOBAL_RATE_LIMIT_MAX_REQUESTS", "600"))
    auth_rate_limit_window_seconds: int = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900")))
    auth_rate_limit_max_requests: int = int(os.getenv("AUTH_RATE_LIMIT_MAX_REQUESTS", os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5")))
    webhook_rate_limit_window_seconds: int = int(os.getenv("WEBHOOK_RATE_LIMIT_WINDOW_SECONDS", "60"))
    webhook_rate_limit_max_requests: int = int(os.getenv("WEBHOOK_RATE_LIMIT_MAX_REQUESTS", "120"))
    max_request_body_bytes: int = int(os.getenv("MAX_REQUEST_BODY_BYTES", "2097152"))
    max_webhook_body_bytes: int = int(os.getenv("MAX_WEBHOOK_BODY_BYTES", "1048576"))
    frontend_telemetry_public_token: str = os.getenv("FRONTEND_TELEMETRY_PUBLIC_TOKEN", "").strip()
    frontend_telemetry_require_token: bool = _env_bool("FRONTEND_TELEMETRY_REQUIRE_TOKEN", os.getenv("APP_ENV", "development").strip().lower() == "production")
    frontend_telemetry_allowed_origins_raw: str = os.getenv("FRONTEND_TELEMETRY_ALLOWED_ORIGINS", os.getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ALLOWED_ORIGINS))
    frontend_telemetry_rate_limit_window_seconds: int = int(os.getenv("FRONTEND_TELEMETRY_RATE_LIMIT_WINDOW_SECONDS", "60"))
    frontend_telemetry_rate_limit_max_events: int = int(os.getenv("FRONTEND_TELEMETRY_RATE_LIMIT_MAX_EVENTS", "60"))
    frontend_telemetry_max_body_bytes: int = int(os.getenv("FRONTEND_TELEMETRY_MAX_BODY_BYTES", "8192"))
    hsts_max_age_seconds: int = int(os.getenv("HSTS_MAX_AGE_SECONDS", "63072000"))
    hsts_include_subdomains: bool = _env_bool("HSTS_INCLUDE_SUBDOMAINS", True)
    hsts_preload: bool = _env_bool("HSTS_PRELOAD", True)
    content_security_policy: str = os.getenv("CONTENT_SECURITY_POLICY", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
    strict_security_startup: bool = _env_bool("STRICT_SECURITY_STARTUP", True)
    startup_init_db: bool = _env_bool("STARTUP_INIT_DB", True)
    startup_db_required: bool = _env_bool("STARTUP_DB_REQUIRED", True)
    request_tracing_enabled: bool = _env_bool("REQUEST_TRACING_ENABLED", True)
    allow_sqlite_for_tests: bool = _env_bool("ALLOW_SQLITE_FOR_TESTS", False)
    waos_e2e_fake_providers: bool = _env_bool("WAOS_E2E_FAKE_PROVIDERS", False)
    voice_media_storage_dir: str = os.getenv("VOICE_MEDIA_STORAGE_DIR", "./.waos-voice-media")
    voice_media_ttl_minutes: int = int(os.getenv("VOICE_MEDIA_TTL_MINUTES", "1440"))
    voice_transcription_webhook_url: str = os.getenv("VOICE_TRANSCRIPTION_WEBHOOK_URL", "")
    voice_transcription_timeout_seconds: int = int(os.getenv("VOICE_TRANSCRIPTION_TIMEOUT_SECONDS", "45"))
    voice_tts_webhook_url: str = os.getenv("VOICE_TTS_WEBHOOK_URL", "")
    voice_tts_timeout_seconds: int = int(os.getenv("VOICE_TTS_TIMEOUT_SECONDS", "30"))
    voice_min_audio_reply_confidence: float = float(os.getenv("VOICE_MIN_AUDIO_REPLY_CONFIDENCE", "0.72"))
    worker_min_poll_seconds: int = int(os.getenv("WORKER_MIN_POLL_SECONDS", "1"))
    worker_max_poll_seconds: int = int(os.getenv("WORKER_MAX_POLL_SECONDS", "15"))
    worker_backpressure_batch_ceiling: int = int(os.getenv("WORKER_BACKPRESSURE_BATCH_CEILING", "200"))
    worker_retry_budget_window_seconds: int = int(os.getenv("WORKER_RETRY_BUDGET_WINDOW_SECONDS", "900"))
    inbound_spam_window_seconds: int = int(os.getenv("INBOUND_SPAM_WINDOW_SECONDS", "60"))
    inbound_spam_max_events: int = int(os.getenv("INBOUND_SPAM_MAX_EVENTS", "12"))
    public_ingest_window_seconds: int = int(os.getenv("PUBLIC_INGEST_WINDOW_SECONDS", "60"))
    public_ingest_max_events: int = int(os.getenv("PUBLIC_INGEST_MAX_EVENTS", "5"))
    openai_circuit_failure_threshold: int = int(os.getenv("OPENAI_CIRCUIT_FAILURE_THRESHOLD", "3"))
    openai_circuit_open_minutes: int = int(os.getenv("OPENAI_CIRCUIT_OPEN_MINUTES", "2"))
    meta_circuit_failure_threshold: int = int(os.getenv("META_CIRCUIT_FAILURE_THRESHOLD", "3"))
    meta_circuit_open_minutes: int = int(os.getenv("META_CIRCUIT_OPEN_MINUTES", "2"))

    @property
    def normalized_database_url(self) -> str:
        raw = self.database_url.strip()
        if not raw:
            if self.app_env.strip().lower() in {"test", "testing", "development", "dev", "local"} or self.allow_sqlite_for_tests:
                return "sqlite:///./.waos-local.db"
            raise ValueError("DATABASE_URL is required in production releases.")
        if raw.startswith("postgres://"):
            return "postgresql://" + raw[len("postgres://"):]
        return raw

    @property
    def database_backend(self) -> str:
        url = self.normalized_database_url
        if url.startswith("postgresql://") or url.startswith("postgresql+"):
            return "postgresql"
        if url.startswith("sqlite:///"):
            if self.app_env.strip().lower() in {"test", "testing", "development", "dev", "local"} or self.allow_sqlite_for_tests:
                return "sqlite"
            raise ValueError("DATABASE_URL must point to PostgreSQL in production releases. SQLite is allowed for development and internal tests.")
        raise ValueError("DATABASE_URL must start with postgresql:// for this release")

    @property
    def sqlite_path(self) -> str:
        if self.normalized_database_url.startswith("sqlite:///"):
            return self.normalized_database_url.replace("sqlite:///", "", 1)
        return "./.waos-local.db"

    @property
    def cors_allowed_origins(self) -> list[str]:
        values = [item.strip() for item in self.cors_allowed_origins_raw.split(",") if item.strip()]
        return values or [DEFAULT_PUBLIC_APP_URL]

    @property
    def frontend_telemetry_allowed_origins(self) -> list[str]:
        values = [item.strip().rstrip("/") for item in self.frontend_telemetry_allowed_origins_raw.split(",") if item.strip()]
        public_app_url = self.public_app_url.strip().rstrip("/")
        if public_app_url and public_app_url not in values:
            values.append(public_app_url)
        return values or [DEFAULT_PUBLIC_APP_URL]

    @property
    def cors_allowed_origin_regex(self) -> str | None:
        value = self.cors_allowed_origin_regex_raw.strip()
        return value or None

    @property
    def allowed_hosts(self) -> list[str]:
        values = [item.strip() for item in self.allowed_hosts_raw.split(",") if item.strip()]
        if not values:
            values = ["app.example.com", "api.example.com"]
        if not self.is_production:
            for host in ["localhost", "127.0.0.1", "testserver", "testclient"]:
                if host not in values:
                    values.append(host)
        return values

    @property
    def trusted_proxy_ips(self) -> list[str]:
        values = [item.strip() for item in self.trusted_proxy_ips_raw.split(",") if item.strip()]
        return values

    @property
    def trusted_proxy_networks(self) -> list[ipaddress._BaseNetwork]:
        networks: list[ipaddress._BaseNetwork] = []
        for value in self.trusted_proxy_ips:
            networks.append(ipaddress.ip_network(value, strict=False))
        return networks

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def app_secret_is_default(self) -> bool:
        return self.app_secret.strip().lower() in DEFAULT_SECRET_SENTINELS

    @property
    def encryption_key_is_default(self) -> bool:
        return self.secret_encryption_key.strip().lower() in DEFAULT_SECRET_SENTINELS or self.secret_encryption_key == self.app_secret

    @property
    def meta_verify_token_is_default(self) -> bool:
        return self.meta_verify_token.strip().lower() in DEFAULT_META_VERIFY_SENTINELS

    @property
    def secure_cookies(self) -> bool:
        return _env_bool("SECURE_COOKIES", self.is_production)

    @property
    def trust_proxy_headers(self) -> bool:
        return _env_bool("TRUST_PROXY_HEADERS", self.is_production)

    @property
    def feature_flags(self) -> dict[str, bool]:
        return {
            "business_hub": True,
            "customer_preview": True,
            "launch_center": True,
            "security_headers": True,
            "session_inventory": True,
            "release_security_gates": True,
        }

    @property
    def minimum_secret_length(self) -> int:
        return 32

    def _validate_url(self, value: str, *, name: str, allow_http: bool) -> None:
        parsed = urlparse(value)
        if parsed.scheme not in ({"https", "http"} if allow_http else {"https"}) or not parsed.netloc:
            allowed = "http/https" if allow_http else "https"
            raise ValueError(f"{name} must be a valid {allowed} URL")


    def validate_ai_provider_alignment(self, *, require_explicit: bool | None = None) -> None:
        require_explicit = self.is_production if require_explicit is None else require_explicit
        explicit_model = os.getenv("OPENAI_MODEL", "").strip()
        explicit_base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        base_url = self.openai_base_url.strip().lower().rstrip("/") + "/"
        model = self.openai_model.strip().lower()
        if require_explicit and not explicit_model:
            raise ValueError("OPENAI_MODEL must be explicitly set in production to avoid silent fallback")
        if require_explicit and not explicit_base_url:
            raise ValueError("OPENAI_BASE_URL must be explicitly set in production to avoid silent fallback")
        if "generativelanguage.googleapis.com" in base_url and not model.startswith("gemini-"):
            raise ValueError("OPENAI_BASE_URL points to Gemini, but OPENAI_MODEL is not a Gemini model")
        if "api.openai.com" in base_url and model.startswith("gemini-"):
            raise ValueError("OPENAI_BASE_URL points to OpenAI, but OPENAI_MODEL is Gemini")
        if self.openai_timeout_seconds < 5 or self.openai_timeout_seconds > 60:
            raise ValueError("OPENAI_TIMEOUT_SECONDS must be between 5 and 60")
        if self.autopilot_max_autofix_rounds < 1 or self.autopilot_max_autofix_rounds > 2:
            raise ValueError("AUTOPILOT_MAX_AUTOFIX_ROUNDS must be between 1 and 2 in this hardened release")

    def validate_runtime(self) -> None:
        if self.db_pool_min_size < 1:
            raise ValueError("DB_POOL_MIN_SIZE must be >= 1")
        if self.db_pool_max_size < self.db_pool_min_size:
            raise ValueError("DB_POOL_MAX_SIZE must be >= DB_POOL_MIN_SIZE")
        if self.db_pool_timeout_seconds < 1:
            raise ValueError("DB_POOL_TIMEOUT_SECONDS must be >= 1")
        if self.default_page_size < 1 or self.max_page_size < self.default_page_size:
            raise ValueError("Pagination settings are invalid")
        if self.access_token_ttl_minutes < 5:
            raise ValueError("ACCESS_TOKEN_TTL_MINUTES must be >= 5")
        if self.refresh_token_ttl_minutes <= self.access_token_ttl_minutes:
            raise ValueError("REFRESH_TOKEN_TTL_MINUTES must be greater than ACCESS_TOKEN_TTL_MINUTES")
        if self.session_idle_timeout_minutes > self.refresh_token_ttl_minutes:
            raise ValueError("SESSION_IDLE_TIMEOUT_MINUTES cannot exceed REFRESH_TOKEN_TTL_MINUTES")
        if self.step_up_window_minutes < 1 or self.step_up_window_minutes > self.session_idle_timeout_minutes:
            raise ValueError("STEP_UP_WINDOW_MINUTES must be between 1 and SESSION_IDLE_TIMEOUT_MINUTES")
        if self.max_sessions_per_user < 1:
            raise ValueError("MAX_SESSIONS_PER_USER must be >= 1")
        if self.login_rate_limit_window_seconds < 60 or self.login_rate_limit_max_attempts < 1:
            raise ValueError("Login rate limit settings are invalid")
        if self.worker_min_poll_seconds < 1 or self.worker_max_poll_seconds < self.worker_min_poll_seconds:
            raise ValueError("Worker poll settings are invalid")
        if self.worker_backpressure_batch_ceiling < self.worker_batch_size:
            raise ValueError("WORKER_BACKPRESSURE_BATCH_CEILING must be >= WORKER_BATCH_SIZE")
        if self.worker_retry_budget_window_seconds < 60:
            raise ValueError("WORKER_RETRY_BUDGET_WINDOW_SECONDS must be >= 60")
        if self.inbound_spam_window_seconds < 10 or self.inbound_spam_max_events < 1:
            raise ValueError("Inbound spam protection settings are invalid")
        if self.public_ingest_window_seconds < 10 or self.public_ingest_max_events < 1:
            raise ValueError("Public ingest rate limit settings are invalid")
        if self.openai_circuit_failure_threshold < 1 or self.openai_circuit_open_minutes < 1:
            raise ValueError("OpenAI circuit breaker settings are invalid")
        if self.ai_workflow_recovery_stale_after_minutes < 1 or self.ai_workflow_recovery_stale_after_minutes > 24 * 60:
            raise ValueError("AI_WORKFLOW_RECOVERY_STALE_AFTER_MINUTES must be between 1 and 1440")
        if self.meta_circuit_failure_threshold < 1 or self.meta_circuit_open_minutes < 1:
            raise ValueError("Meta circuit breaker settings are invalid")
        if self.is_production and self.waos_e2e_fake_providers:
            raise ValueError("WAOS_E2E_FAKE_PROVIDERS cannot be enabled in production")
        if self.is_production and not self.startup_db_required:
            raise ValueError("STARTUP_DB_REQUIRED cannot be false in production")
        if "*" in self.cors_allowed_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS cannot contain '*' when credentials are enabled")
        if not self.allowed_hosts:
            raise ValueError("ALLOWED_HOSTS cannot be empty")
        self._validate_url(self.public_app_url, name="PUBLIC_APP_URL", allow_http=not self.is_production)
        self._validate_url(self.api_base_url, name="API_BASE_URL", allow_http=not self.is_production)
        self._validate_url(self.api_internal_url, name="API_INTERNAL_URL", allow_http=True)
        self._validate_url(self.openai_base_url, name="OPENAI_BASE_URL", allow_http=False)
        self.validate_ai_provider_alignment()
        self._validate_url(self.meta_graph_api_base, name="META_GRAPH_API_BASE", allow_http=False)
        if self.is_production:
            if not self.secure_cookies:
                raise ValueError("SECURE_COOKIES must be enabled in production")
            if self.trust_proxy_headers and not self.trusted_proxy_ips:
                raise ValueError("TRUSTED_PROXY_IPS must be configured when TRUST_PROXY_HEADERS is enabled in production")
            if self.trust_proxy_headers:
                try:
                    self.trusted_proxy_networks
                except ValueError as exc:
                    raise ValueError("TRUSTED_PROXY_IPS contains invalid IP/CIDR entry") from exc
            if any(host == "*" for host in self.allowed_hosts):
                raise ValueError("ALLOWED_HOSTS cannot contain '*' in production")
            if not self.security_hardening_enabled:
                raise ValueError("SECURITY_HARDENING_ENABLED cannot be disabled in production")
            if not self.enforce_https:
                raise ValueError("ENFORCE_HTTPS cannot be disabled in production")
            if not self.require_signed_webhooks:
                raise ValueError("REQUIRE_SIGNED_WEBHOOKS cannot be disabled in production")
            if self.security_rate_limit_enabled and self.rate_limit_backend == "memory":
                raise ValueError("RATE_LIMIT_BACKEND must be redis, valkey, upstash, or gateway in production")
            if self.security_rate_limit_enabled and self.rate_limit_backend == "gateway" and not self.rate_limit_gateway_enforced:
                raise ValueError("RATE_LIMIT_GATEWAY_ENFORCED must be true when RATE_LIMIT_BACKEND=gateway in production")
            if self.max_request_body_bytes > 10 * 1024 * 1024:
                raise ValueError("MAX_REQUEST_BODY_BYTES must be <= 10MiB in production")
            if self.max_webhook_body_bytes > 5 * 1024 * 1024:
                raise ValueError("MAX_WEBHOOK_BODY_BYTES must be <= 5MiB in production")
        if self.security_hardening_enabled:
            allowed_rate_backends = {"memory", "redis", "valkey", "upstash", "gateway"}
            if self.rate_limit_backend not in allowed_rate_backends:
                raise ValueError("RATE_LIMIT_BACKEND must be one of: gateway, memory, redis, upstash, valkey")
            if self.rate_limit_backend in {"redis", "valkey", "upstash"} and not self.rate_limit_redis_url:
                raise ValueError("RATE_LIMIT_REDIS_URL or REDIS_URL is required for distributed rate limiting")
            if self.rate_limit_redis_timeout_seconds <= 0:
                raise ValueError("RATE_LIMIT_REDIS_TIMEOUT_SECONDS must be > 0")
            if self.rate_limit_memory_max_buckets < 100:
                raise ValueError("RATE_LIMIT_MEMORY_MAX_BUCKETS must be >= 100")
            if self.rate_limit_memory_eviction_batch < 1:
                raise ValueError("RATE_LIMIT_MEMORY_EVICTION_BATCH must be >= 1")
            if self.max_request_body_bytes < 1024:
                raise ValueError("MAX_REQUEST_BODY_BYTES must be at least 1024")
            if self.max_webhook_body_bytes < 1024:
                raise ValueError("MAX_WEBHOOK_BODY_BYTES must be at least 1024")
            for name, value in {
                "GLOBAL_RATE_LIMIT_WINDOW_SECONDS": self.global_rate_limit_window_seconds,
                "GLOBAL_RATE_LIMIT_MAX_REQUESTS": self.global_rate_limit_max_requests,
                "AUTH_RATE_LIMIT_WINDOW_SECONDS": self.auth_rate_limit_window_seconds,
                "AUTH_RATE_LIMIT_MAX_REQUESTS": self.auth_rate_limit_max_requests,
                "WEBHOOK_RATE_LIMIT_WINDOW_SECONDS": self.webhook_rate_limit_window_seconds,
                "WEBHOOK_RATE_LIMIT_MAX_REQUESTS": self.webhook_rate_limit_max_requests,
                "HSTS_MAX_AGE_SECONDS": self.hsts_max_age_seconds,
            }.items():
                if int(value) < 1:
                    raise ValueError(f"{name} must be >= 1")

    def public_summary(self) -> dict[str, object]:
        return {
            "name": self.app_name,
            "environment": self.app_env,
            "version": self.app_version,
            "database_backend": self.database_backend,
            "default_timezone": self.default_timezone,
            "api_base_url": self.api_base_url,
            "api_internal_url": self.api_internal_url,
            "run_bootstrap_seed": self.run_bootstrap_seed,
            "auto_run_migrations": self.auto_run_migrations,
            "db_pool_min_size": self.db_pool_min_size,
            "db_pool_max_size": self.db_pool_max_size,
            "db_pool_timeout_seconds": self.db_pool_timeout_seconds,
            "default_page_size": self.default_page_size,
            "startup_init_db": self.startup_init_db,
            "startup_db_required": self.startup_db_required,
            "request_tracing_enabled": self.request_tracing_enabled,
            "waos_e2e_fake_providers": self.waos_e2e_fake_providers,
            "max_page_size": self.max_page_size,
            "runtime_cache_ttl_seconds": self.runtime_cache_ttl_seconds,
            "web_concurrency": self.web_concurrency,
            "worker_batch_size": self.worker_batch_size,
            "voice_media_ttl_minutes": self.voice_media_ttl_minutes,
            "voice_transcription_webhook_enabled": bool(self.voice_transcription_webhook_url),
            "voice_tts_webhook_enabled": bool(self.voice_tts_webhook_url),
            "worker_min_poll_seconds": self.worker_min_poll_seconds,
            "worker_max_poll_seconds": self.worker_max_poll_seconds,
            "worker_backpressure_batch_ceiling": self.worker_backpressure_batch_ceiling,
            "worker_retry_budget_window_seconds": self.worker_retry_budget_window_seconds,
            "inbound_spam_window_seconds": self.inbound_spam_window_seconds,
            "inbound_spam_max_events": self.inbound_spam_max_events,
            "public_ingest_window_seconds": self.public_ingest_window_seconds,
            "public_ingest_max_events": self.public_ingest_max_events,
            "openai_circuit_failure_threshold": self.openai_circuit_failure_threshold,
            "openai_circuit_open_minutes": self.openai_circuit_open_minutes,
            "meta_circuit_failure_threshold": self.meta_circuit_failure_threshold,
            "meta_circuit_open_minutes": self.meta_circuit_open_minutes,
            "public_app_url": self.public_app_url,
            "cors_allowed_origins": self.cors_allowed_origins,
            "secure_cookies": self.secure_cookies,
            "otel_export_enabled": self.otel_export_enabled,
            "otel_export_endpoint": self.otel_export_endpoint,
            "otel_service_name": self.otel_service_name,
            "datadog_otlp_endpoint": self.datadog_otlp_endpoint,
            "datadog_api_key_present": self.datadog_api_key_present,
            "new_relic_otlp_endpoint": self.new_relic_otlp_endpoint,
            "new_relic_license_key_present": self.new_relic_license_key_present,
            "feature_flags": self.feature_flags,
            "access_token_ttl_minutes": self.access_token_ttl_minutes,
            "refresh_token_ttl_minutes": self.refresh_token_ttl_minutes,
            "session_idle_timeout_minutes": self.session_idle_timeout_minutes,
            "login_rate_limit_window_seconds": self.login_rate_limit_window_seconds,
            "login_rate_limit_max_attempts": self.login_rate_limit_max_attempts,
            "security_hardening_enabled": self.security_hardening_enabled,
            "enforce_https": self.enforce_https,
            "reject_untrusted_proxy_headers": self.reject_untrusted_proxy_headers,
            "require_signed_webhooks": self.require_signed_webhooks,
            "security_rate_limit_enabled": self.security_rate_limit_enabled,
            "rate_limit_backend": self.rate_limit_backend,
            "rate_limit_redis_configured": bool(self.rate_limit_redis_url),
            "rate_limit_memory_max_buckets": self.rate_limit_memory_max_buckets,
            "rate_limit_gateway_enforced": self.rate_limit_gateway_enforced,
            "global_rate_limit_window_seconds": self.global_rate_limit_window_seconds,
            "global_rate_limit_max_requests": self.global_rate_limit_max_requests,
            "auth_rate_limit_window_seconds": self.auth_rate_limit_window_seconds,
            "auth_rate_limit_max_requests": self.auth_rate_limit_max_requests,
            "webhook_rate_limit_window_seconds": self.webhook_rate_limit_window_seconds,
            "webhook_rate_limit_max_requests": self.webhook_rate_limit_max_requests,
            "max_request_body_bytes": self.max_request_body_bytes,
            "max_webhook_body_bytes": self.max_webhook_body_bytes,
            "frontend_telemetry_allowed_origins": self.frontend_telemetry_allowed_origins,
            "frontend_telemetry_require_token": self.frontend_telemetry_require_token,
            "frontend_telemetry_rate_limit_window_seconds": self.frontend_telemetry_rate_limit_window_seconds,
            "frontend_telemetry_rate_limit_max_events": self.frontend_telemetry_rate_limit_max_events,
            "frontend_telemetry_max_body_bytes": self.frontend_telemetry_max_body_bytes,
            "hsts_max_age_seconds": self.hsts_max_age_seconds,
            "hsts_include_subdomains": self.hsts_include_subdomains,
            "hsts_preload": self.hsts_preload,
        }


settings = Settings()
