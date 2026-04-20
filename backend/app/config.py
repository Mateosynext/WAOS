from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


DEFAULT_PUBLIC_APP_URL = "https://app.example.com"
DEFAULT_API_BASE_URL = "https://api.example.com"
DEFAULT_API_INTERNAL_URL = "http://backend:8000"
DEFAULT_CORS_ALLOWED_ORIGINS = DEFAULT_PUBLIC_APP_URL
DEFAULT_ALLOWED_HOSTS = "app.example.com,api.example.com"
DEFAULT_SECRET_SENTINELS = {"", "waos-dev-secret-key", "changeme", "change_me", "replace_me", "example", "default"}
DEFAULT_META_VERIFY_SENTINELS = {"", "changeme", "change_me", "replace_me", "example", "default"}


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
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
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
    web_concurrency: int = int(os.getenv("WEB_CONCURRENCY", "2"))
    worker_batch_size: int = int(os.getenv("WORKER_BATCH_SIZE", "50"))
    access_token_ttl_minutes: int = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "60"))
    refresh_token_ttl_minutes: int = int(os.getenv("REFRESH_TOKEN_TTL_MINUTES", "720"))
    session_idle_timeout_minutes: int = int(os.getenv("SESSION_IDLE_TIMEOUT_MINUTES", "120"))
    step_up_window_minutes: int = int(os.getenv("STEP_UP_WINDOW_MINUTES", "15"))
    max_sessions_per_user: int = int(os.getenv("MAX_SESSIONS_PER_USER", "5"))
    login_rate_limit_window_seconds: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900"))
    login_rate_limit_max_attempts: int = int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5"))
    trusted_proxy_ips_raw: str = os.getenv("TRUSTED_PROXY_IPS", "")
    strict_security_startup: bool = _env_bool("STRICT_SECURITY_STARTUP", True)
    startup_init_db: bool = _env_bool("STARTUP_INIT_DB", True)
    startup_db_required: bool = _env_bool("STARTUP_DB_REQUIRED", False if os.getenv("APP_ENV", "development").strip().lower() == "production" else True)
    request_tracing_enabled: bool = _env_bool("REQUEST_TRACING_ENABLED", True)
    allow_sqlite_for_tests: bool = _env_bool("ALLOW_SQLITE_FOR_TESTS", False)
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
        if self.meta_circuit_failure_threshold < 1 or self.meta_circuit_open_minutes < 1:
            raise ValueError("Meta circuit breaker settings are invalid")
        if "*" in self.cors_allowed_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS cannot contain '*' when credentials are enabled")
        if not self.allowed_hosts:
            raise ValueError("ALLOWED_HOSTS cannot be empty")
        self._validate_url(self.public_app_url, name="PUBLIC_APP_URL", allow_http=not self.is_production)
        self._validate_url(self.api_base_url, name="API_BASE_URL", allow_http=not self.is_production)
        self._validate_url(self.api_internal_url, name="API_INTERNAL_URL", allow_http=True)
        self._validate_url(self.openai_base_url, name="OPENAI_BASE_URL", allow_http=False)
        self._validate_url(self.meta_graph_api_base, name="META_GRAPH_API_BASE", allow_http=False)
        if self.is_production:
            if not self.secure_cookies:
                raise ValueError("SECURE_COOKIES must be enabled in production")
            if self.trust_proxy_headers and not self.trusted_proxy_ips:
                raise ValueError("TRUSTED_PROXY_IPS must be configured when TRUST_PROXY_HEADERS is enabled in production")
            if any(host == "*" for host in self.allowed_hosts):
                raise ValueError("ALLOWED_HOSTS cannot contain '*' in production")

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
        }


settings = Settings()
