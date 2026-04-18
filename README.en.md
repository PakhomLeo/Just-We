# Just-We

[![CI](https://github.com/PakhomLeo/dynamicwepubmonitor/actions/workflows/ci.yml/badge.svg)](https://github.com/PakhomLeo/dynamicwepubmonitor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文](README.md) | English

Just-We is a self-hosted platform for monitoring WeChat Official Account content.
It brings collector accounts, monitored accounts, article collection, localized
media, AI relevance analysis, exports, Feed access, rate limits, proxies, task
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
- Configurable AI analysis for text, image, article type judgment, and combined
  structured decisions.
- Feed output, aggregate Feed tokens, article export jobs, and download paths.
- Proxy and rate-limit management with service bindings, failure cooldowns,
  success rate tracking, proxy kind, rotation mode, and policy configuration.
- Task logs, operation logs, failure categories, and runtime statistics.
- Single-container production web serving with SPA deep-link fallback.

## Project Layout

```text
app/         FastAPI application, API routers, services, repositories, tasks, models
alembic/     PostgreSQL migration chain
frontend/    Vue 3, Vite, Element Plus, Pinia admin console
tests/       Backend regression tests
docs/        Deployment, configuration, design, and reference documentation
```

## Technology Stack

- Backend: FastAPI, SQLAlchemy Async, Alembic, Pydantic Settings, APScheduler
- Frontend: Vue 3, Vite, Element Plus, Pinia, Vue Router, Axios
- Database: PostgreSQL
- Cache and runtime state: Redis
- Deployment: multi-stage Dockerfile and Docker Compose

## Quick Start with Docker

Docker Compose is the recommended way to try or self-host Just-We:

```bash
docker compose up -d --build
```

Then open:

- Web UI and API: <http://localhost:8000>
- Health check: <http://localhost:8000/health>
- API docs: <http://localhost:8000/docs>

Default bootstrap account:

- Username: `admin`
- Password: `admin123`

Before exposing the service, set a strong `JWT_SECRET_KEY` and change the
default admin password. See [Docker deployment](docs/docker.md) for upgrade,
backup, restore, logs, and reset commands.

## Local Development

Requirements:

- Python 3.12
- Node.js 20.19+ or 22.12+
- PostgreSQL
- Redis

Install backend dependencies:

```bash
uv sync
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

Copy the local environment example and adjust database credentials:

```bash
cp .env.example .env
```

Run migrations:

```bash
uv run alembic upgrade head
```

Start the backend:

```bash
uv run uvicorn app.main:app --reload
```

Start the frontend dev server:

```bash
cd frontend
npm run dev
```

Default local URLs:

- Frontend dev server: <http://localhost:5173>
- Backend API: <http://localhost:8000>

## Configuration

Configuration is loaded from environment variables:

- `.env.example` for local development.
- `.env.docker.example` for Docker-specific deployment overrides.

Key production settings include `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`,
`MEDIA_ROOT`, `FRONTEND_DIST_PATH`, `LLM_API_URL`, `LLM_API_KEY`,
`WEREAD_PLATFORM_URL`, and the default admin bootstrap variables. See
[Configuration](docs/configuration.md) for the full table and operational notes.

## Testing

Backend checks:

```bash
uv run ruff check app tests scripts
uv run pytest -q
uv run python -m compileall app tests scripts
```

Frontend build:

```bash
cd frontend
npm run build
```

Docker checks:

```bash
docker compose config
docker compose build
```

## Documentation

- [Technical design](docs/technical-design.md)
- [Docker deployment](docs/docker.md)
- [Configuration](docs/configuration.md)
- [Project expectations](docs/项目期望.md)
- [Frontend details](docs/前端详情.md)
- [Backend details](docs/后端详情.md)
- [Reference project notes](docs/参考项目详情.md)

`external_references/` is a local-only reference directory. It is ignored by Git
and excluded from the Docker build context; it is not part of the open source
release.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Keep
changes focused, add tests for backend behavior changes, and do not commit
runtime data, credentials, media, logs, frontend build output, or
`external_references/`.

## Security

Please report vulnerabilities privately. See [SECURITY.md](SECURITY.md) for
supported versions, reporting guidance, and deployment security notes.

## License

Just-We is licensed under the [MIT License](LICENSE).
