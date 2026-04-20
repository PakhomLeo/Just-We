# Configuration

Just—We uses environment variables through `pydantic-settings`.

- Local development: copy `.env.example` to `.env`.
- Docker deployment: use the defaults in `docker-compose.yml`, or copy
  `.env.docker.example` to `.env.docker` and pass it with `--env-file`.
  Docker override names are prefixed with `JUST_WE_*` so a local development
  `.env` file is not accidentally injected into Compose interpolation.

## Core Settings

| Variable | Default | Description |
| --- | --- | --- |
| `APP_ENV` | `development` | Application environment, `development` or `production`. |
| `DEBUG` | `true` | Enables debug behavior where supported. |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/dynamicwepubmonitor` | SQLAlchemy async database URL. Docker uses host `postgres`. |
| `DATABASE_ECHO` | `false` | Enables verbose SQLAlchemy query logging. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL. Docker uses host `redis`. |
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT signing secret. Must be changed for production. |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime. Docker defaults to `1440`. |
| `MEDIA_ROOT` | `media` | Local directory for localized article media. |
| `MEDIA_URL_PREFIX` | `/media` | Public URL prefix for localized media files. |
| `FRONTEND_DIST_PATH` | `frontend/dist` | Directory containing the built Vue app for production static serving. |

## Default Admin Bootstrap

| Variable | Default | Description |
| --- | --- | --- |
| `ENSURE_DEFAULT_ADMIN` | `true` | Creates or repairs the default admin at startup. |
| `DEFAULT_ADMIN_ALIAS` | `admin` | Login alias for the default admin. |
| `DEFAULT_ADMIN_EMAIL` | `admin@admin.com` | Email for the default admin. |
| `DEFAULT_ADMIN_PASSWORD` | `admin123` | Password used when the account is created or repaired. |

Change the default password immediately after first login. For hardened
deployments, disable default bootstrap after provisioning an administrator.

## AI Analysis

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_API_URL` | `https://api.example.com/v1/chat/completions` | OpenAI-compatible chat completion endpoint. |
| `LLM_API_KEY` | empty | Provider API key. Leave empty to validate failure and fallback behavior only. |
| `LLM_MODEL` | `gpt-4o` | Model name sent to the provider. |
| `HIGH_RELEVANCE_THRESHOLD` | `0.8` | Threshold for high-relevance notifications. |
| `AI_CONSECUTIVE_LOW_THRESHOLD` | `3` | Consecutive low-relevance threshold. |

These environment variables seed the first AI configuration row. The settings
page then stores the active text and image AI configuration in the database:

- Text AI: API URL, API key, model, text analysis focus, and target-type
  judgment prompt.
- Image AI: API URL, API key, model, image analysis focus, and timeout.
- `POST /api/system/ai-config/test` tests the current form values with a
  dedicated synthetic payload. It does not send an existing article body or
  production image to the provider.
- Article fetching and AI analysis are decoupled. Successful article fetches
  are saved with `ai_analysis_status=pending`; background AI tasks update the
  article later to `success`, `failed`, or `skipped`.

## WeRead and QR Login

| Variable | Default | Description |
| --- | --- | --- |
| `QR_CODE_EXPIRE_SECONDS` | `180` | QR login expiration window. |
| `WEREAD_PLATFORM_URL` | `https://weread.111965.xyz` | WeRead-compatible platform endpoint. Empty disables that integration path. |
| `WEREAD_PLATFORM_TIMEOUT_SECONDS` | `30` | Timeout for WeRead platform API requests. |
| `WEREAD_PLATFORM_EXPIRE_FAILURE_THRESHOLD` | `2` | Consecutive platform credential failures before a WeRead account is marked expired. |
| `WEREAD_PLATFORM_CREDENTIAL_COOLDOWN_MINUTES` | `60` | Cooldown after the first suspected platform credential failure. |

External WeChat, WeRead, AI, and proxy services are optional for local
usability testing. Without credentials, the UI should still save configuration,
show clear states, and return understandable failures.

WeRead-compatible platforms have account and IP-level request limits. Just—We
does not run article-list probes during periodic health checks; it validates the
token during real list fetches, cools down after a first suspected credential
failure, and only marks the account expired after repeated failures. Keep the
QR login option that auto-exits after 24 hours unchecked, and spread monitored
accounts across multiple WeRead accounts when you need higher fetch volume.

## Proxy Service Bindings

Proxy records are created and edited from the proxy management page. The current
UI intentionally exposes two operational profiles for WeChat traffic:

| Profile | Backing kind | Default service keys | Purpose |
| --- | --- | --- | --- |
| Static residential | `residential_static` | `mp_admin_login`, `weread_login`, `mp_list`, `weread_list` | QR login and article-list fetches that need a stable exit IP. |
| Dynamic residential | `residential_rotating` | `mp_detail`, `weread_detail`, `image_proxy` | Article detail parsing and localized image downloading. |

Datacenter proxies remain supported by the backend for `ai` service bindings,
but they are not offered as a default WeChat proxy profile in the simplified
proxy form. Existing advanced proxy kinds are preserved for compatibility and
can still be returned by the API.

## Weight and Scheduling

| Variable | Default | Description |
| --- | --- | --- |
| `WEIGHT_FREQUENCY_RATIO` | `0.35` | Frequency contribution to dynamic account weight. |
| `WEIGHT_RECENCY_RATIO` | `0.25` | Recency contribution to dynamic account weight. |
| `WEIGHT_RELEVANCE_RATIO` | `0.25` | AI relevance contribution to dynamic account weight. |
| `WEIGHT_STABILITY_RATIO` | `0.15` | Stability contribution to dynamic account weight. |
| `TIER_THRESHOLD_TIER1` | `80` | Tier 1 minimum score. |
| `TIER_THRESHOLD_TIER2` | `65` | Tier 2 minimum score. |
| `TIER_THRESHOLD_TIER3` | `50` | Tier 3 minimum score. |
| `TIER_THRESHOLD_TIER4` | `35` | Tier 4 minimum score. |
| `CHECK_INTERVAL_TIER1` | `24` | Tier 1 fetch interval in hours. |
| `CHECK_INTERVAL_TIER2` | `48` | Tier 2 fetch interval in hours. |
| `CHECK_INTERVAL_TIER3` | `72` | Tier 3 fetch interval in hours. |
| `CHECK_INTERVAL_TIER4` | `144` | Tier 4 fetch interval in hours. |
| `CHECK_INTERVAL_TIER5` | `336` | Tier 5 fetch interval in hours. |
| `COLLECTOR_HEALTH_CHECK_HOUR` | `23` | Daily automatic collector account health-check hour, in Asia/Shanghai time. |
| `COLLECTOR_HEALTH_CHECK_MINUTE` | `30` | Daily automatic collector account health-check minute, in Asia/Shanghai time. |

## SMTP and Notifications

SMTP settings are managed from the system settings page and persisted in the
database. Treat SMTP credentials and recipient data as sensitive operational
data.

## Sensitive Data

Do not commit `.env`, `.env.docker`, AI keys, proxy credentials, QR sessions,
media files, logs, or database backups. `external_references/` is ignored and
excluded from Docker builds because it is only local reference material.
