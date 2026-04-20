# Just—We

[![CI](https://github.com/PakhomLeo/Just-We/actions/workflows/ci.yml/badge.svg)](https://github.com/PakhomLeo/Just-We/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文](README.md) | English

Just—We is a self-hosted platform for monitoring WeChat Official Account content.
It brings collector accounts, monitored accounts, article collection, localized
media, background AI analysis, exports, Feed access, rate limits, proxies, task
logs, and system administration into one web console.

The project is intentionally scoped around an operational monitoring workflow,
not a generic crawler framework. The fastest production-like path is the Docker
Compose deployment, which starts the app, PostgreSQL, and Redis with one command.
The app container serves both the FastAPI API and the built Vue frontend.

## Features

- User authentication and role-based access for `admin`, `operator`, and
  `viewer`.
- Collector account management with QR login, health checks, expiry detection,
  risk states, and failure records.
- Monitored account management with `biz` / `fakeid` parsing, per-user
  ownership, tiering, scheduling strategy, and manual fetch triggers.
- Article collection with title, text, rich HTML, cover image, publish time,
  fetch mode, content fingerprint, source metadata, and localized images.
- Configurable text and image AI analysis with dedicated connectivity tests,
  article type judgment, and combined structured decisions. Articles are saved
  by the fetch pipeline first, then queued for background AI processing.
- Feed output, aggregate Feed tokens, article export jobs, and download paths.
- Proxy and rate-limit management with service bindings, failure cooldowns, and
  success rate tracking. Static residential proxies are used for login and list
  fetches, dynamic residential proxies for article parsing and image downloads,
  and datacenter proxies for AI requests.
- Task logs, operation logs, failure categories, and runtime statistics.
- Single-container production web serving with SPA deep-link fallback.

## Project Layout

```text
app/         FastAPI application, API routers, services, repositories, tasks, models
alembic/     PostgreSQL migration chain
frontend/    Vue 3, Vite, Element Plus, Pinia admin console
tests/       Backend regression tests
docs/        Docker deployment, configuration, and technical design documentation
```

## Technology Stack

- Backend: FastAPI, SQLAlchemy Async, Alembic, Pydantic Settings, APScheduler
- Frontend: Vue 3, Vite, Element Plus, Pinia, Vue Router, Axios
- Database: PostgreSQL
- Cache and runtime state: Redis
- Deployment: multi-stage Dockerfile and Docker Compose

## Quick Start with Docker

Published multi-architecture image:

```bash
docker pull ghcr.io/pakhomleo/just-we:latest
```

Users can deploy the full `app + PostgreSQL + Redis` stack with one command.
The command creates a deployment directory, writes `.env`, and reads the release
Compose file from the image itself:

```bash
mkdir -p just-we && cd just-we && printf 'JUST_WE_JWT_SECRET_KEY=%s\nJUST_WE_DEFAULT_ADMIN_PASSWORD=admin123\n' "$(openssl rand -hex 32)" > .env && docker run --rm ghcr.io/pakhomleo/just-we:latest cat /app/docker-compose.release.yml | docker compose -p just-we -f - up -d
```

Then open:

- Web UI and API: <http://localhost:8000>
- Health check: <http://localhost:8000/health>
- API docs: <http://localhost:8000/docs>

Default bootstrap account:

- Username: `admin`
- Password: `admin123`

Before exposing the service, set a strong `JWT_SECRET_KEY` and change the
default admin password. See [Docker deployment](docs/docker.md) and
[Configuration](docs/configuration.md) for deployment, upgrade, backup, restore,
logs, reset commands, and environment variables.

## Documentation

- [Technical design](docs/technical-design.md)
- [Docker deployment](docs/docker.md)
- [Configuration](docs/configuration.md)

`external_references/` is a local-only reference directory. It is ignored by Git
and excluded from the Docker build context; it is not part of the open source
release.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Keep
changes focused, and do not commit runtime data, credentials, media, logs,
frontend build output, or `external_references/`.

## Security

Please report vulnerabilities privately. See [SECURITY.md](SECURITY.md) for
supported versions, reporting guidance, and deployment security notes.

## License

Just—We is licensed under the [MIT License](LICENSE).
