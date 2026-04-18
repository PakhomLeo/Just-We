# Just-We

[![CI](https://github.com/PakhomLeo/dynamicwepubmonitor/actions/workflows/ci.yml/badge.svg)](https://github.com/PakhomLeo/dynamicwepubmonitor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Just-We is a FastAPI and Vue 3 platform for monitoring WeChat Official Account
content. It manages collector accounts, monitored accounts, article collection,
localized media, AI relevance analysis, exports, Feed access, rate limits,
proxies, task logs, and system administration from one web console.

The project is designed for self-hosted operation. The fastest production-like
path is the Docker Compose deployment, which starts the app, PostgreSQL, and
Redis with one command.

## Features

- User authentication and role-based access for `admin`, `operator`, and
  `viewer`.
- Collector account management with QR-login flows, health checks, expiry
  detection, and failure states.
- Monitored account management with `biz` / `fakeid` parsing, owner isolation,
  tiering, scheduling strategy, and manual fetch triggers.
- Article collection with rich content, media localization, detail pages,
  export workflows, and Feed tokens.
- AI analysis, configurable provider settings, relevance thresholds, and
  notification hooks.
- Proxy, rate-limit, weight configuration, task log, audit log, system user, and
  system setting pages.
- Single-container web serving for production builds, including SPA deep-link
  refresh support.

## Architecture

```text
app/         FastAPI application, API routers, services, repositories, tasks
alembic/     PostgreSQL migration chain
frontend/    Vue 3, Vite, Element Plus, Pinia admin console
tests/       Backend regression tests
docs/        Deployment, configuration, and project reference documentation
```

Runtime dependencies:

- Python 3.12
- Node.js 20.19+ or 22.12+ for frontend builds
- PostgreSQL
- Redis

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

Configuration is loaded from environment variables. The main examples are:

- `.env.example` for local development.
- `.env.docker.example` for Docker-specific deployment overrides.

Key production settings include `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`,
`MEDIA_ROOT`, `FRONTEND_DIST_PATH`, `LLM_API_URL`, `LLM_API_KEY`,
`WEREAD_PLATFORM_URL`, and the default admin bootstrap variables.

See [Configuration](docs/configuration.md) for the full table and operational
notes.

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
