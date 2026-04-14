from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_PUBLIC_APP_URL = "https://app.example.com"
DEFAULT_API_BASE_URL = "https://api.example.com"
DEFAULT_API_INTERNAL_URL = "http://backend:8000"
DEFAULT_CORS_ALLOWED_ORIGINS = DEFAULT_PUBLIC_APP_URL
DEFAULT_ALLOWED_HOSTS = "app.example.com,api.example.com"
DEFAULT_SECRET_SENTINELS = {""}
DEFAULT_META_VERIFY_SENTINELS = {""}


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
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./waos.db")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    meta_graph_api_base: str = os.getenv("META_GRAPH_API_BASE", "https://graph.facebook.com/v23.0")
    meta_verify_token: str = os.getenv("META_VERIFY_TOKEN", "")
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "America/Mexico_City")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    sentry_dsn: str = os.getenv("SENTRY_DSN", "")
    cors_allowed_origins_raw: str = os.getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS_ALLOWED_ORIGINS)
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
    allow_sqlite_for_tests: bool = _env_bool("ALLOW_SQLITE_FOR_TESTS", False)

    @property
    def normalized_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            return "postgresql://" + self.database_url[len("postgres://"):]
        return self.database_url

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
        return "./waos.db"

    @property
    def cors_allowed_origins(self) -> list[str]:
        values = [item.strip() for item in self.cors_allowed_origins_raw.split(",") if item.strip()]
        return values or [DEFAULT_PUBLIC_APP_URL]

    @property
    def allowed_hosts(self) -> list[str]:
        values = [item.strip() for item in self.allowed_hosts_raw.split(",") if item.strip()]
        return values or ["app.example.com", "api.example.com"]

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
            "max_page_size": self.max_page_size,
            "runtime_cache_ttl_seconds": self.runtime_cache_ttl_seconds,
            "web_concurrency": self.web_concurrency,
            "worker_batch_size": self.worker_batch_size,
            "public_app_url": self.public_app_url,
            "cors_allowed_origins": self.cors_allowed_origins,
            "secure_cookies": self.secure_cookies,
            "feature_flags": self.feature_flags,
            "access_token_ttl_minutes": self.access_token_ttl_minutes,
            "refresh_token_ttl_minutes": self.refresh_token_ttl_minutes,
            "session_idle_timeout_minutes": self.session_idle_timeout_minutes,
            "login_rate_limit_window_seconds": self.login_rate_limit_window_seconds,
            "login_rate_limit_max_attempts": self.login_rate_limit_max_attempts,
        }


settings = Settings()
