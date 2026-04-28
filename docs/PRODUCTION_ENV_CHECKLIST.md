# WAOS Production Environment Checklist

This checklist is the final production gate for WAOS.

## Backend / Render

Required production variables:

```env
APP_ENV=production
APP_VERSION=0.17.5
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/waos
PUBLIC_APP_URL=https://YOUR-FRONTEND-DOMAIN
API_BASE_URL=https://YOUR-BACKEND-DOMAIN
API_INTERNAL_URL=https://YOUR-BACKEND-DOMAIN
CORS_ALLOWED_ORIGINS=https://YOUR-FRONTEND-DOMAIN
ALLOWED_HOSTS=YOUR-BACKEND-HOSTNAME
APP_SECRET=GENERATE_WITH_OPENSSL_RAND_HEX_32
SECRET_ENCRYPTION_KEY=GENERATE_WITH_OPENSSL_RAND_HEX_32
META_VERIFY_TOKEN=GENERATE_WITH_OPENSSL_RAND_HEX_32
META_APP_SECRET=YOUR_META_APP_SECRET
SECURE_COOKIES=true
TRUST_PROXY_HEADERS=true
ENABLE_API_DOCS=false
SECURITY_HARDENING_ENABLED=true
ENFORCE_HTTPS=true
REQUIRE_SIGNED_WEBHOOKS=true
SECURITY_RATE_LIMIT_ENABLED=true
STARTUP_DB_REQUIRED=true
AUTO_RUN_MIGRATIONS=true
RUN_BOOTSTRAP_SEED=false
WAOS_E2E_FAKE_PROVIDERS=false
OPENAI_API_KEY=YOUR_PROVIDER_KEY
OPENAI_MODEL=gemini-2.0-flash
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
WAOS_REQUIRE_OBSERVABILITY=false
```

Generate secrets with:

```bash
openssl rand -hex 32
```

Generate different values for APP_SECRET, SECRET_ENCRYPTION_KEY, and META_VERIFY_TOKEN.

## Frontend / Vercel

Required production variables:

```env
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
NEXT_PUBLIC_API_BASE_URL=https://YOUR-BACKEND-DOMAIN
API_BASE_URL=https://YOUR-BACKEND-DOMAIN
API_INTERNAL_URL=https://YOUR-BACKEND-DOMAIN
NEXT_PUBLIC_APP_URL=https://YOUR-FRONTEND-DOMAIN
PUBLIC_APP_URL=https://YOUR-FRONTEND-DOMAIN
WAOS_ALLOW_ENV_FALLBACK=false
NEXT_PUBLIC_ENABLE_AI_COMMAND_CENTER=true
NEXT_PUBLIC_ENABLE_MANUAL_BOT_CREATE=false
NEXT_PUBLIC_ENABLE_AI_WORKFLOW_STREAM=true
NEXT_PUBLIC_ENABLE_AI_OPS_INSPECTOR=false
```

## Final go/no-go

Before production traffic, verify:

- Backend `/health` responds successfully.
- Frontend build succeeds.
- Login works.
- Dashboard loads.
- Bot creation works.
- Bot Studio opens.
- Meta webhook verification works.
- AI provider responds with the real key.
- Render and Vercel logs have no startup errors.
