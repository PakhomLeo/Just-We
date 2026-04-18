# Docker Deployment

This guide runs Just-We as a single app container plus PostgreSQL and Redis:

- `app`: FastAPI API, scheduled tasks, media serving, and built Vue static files.
- `postgres`: PostgreSQL 16 with a named volume.
- `redis`: Redis 7 with a named volume.

The default entry point is `http://localhost:8000`.

## Requirements

- Docker Engine with Compose v2.
- A host port `8000` available.

## One-command Start

```bash
docker compose up -d --build
```

Open:

- Web UI: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

Default bootstrap account:

- Username: `admin`
- Password: `admin123`

Change the password after first login. For any public deployment, set a strong
`JWT_SECRET_KEY`.

## Optional Environment Overrides

The compose file works without an env file. To keep deployment-specific values,
copy the example:

```bash
cp .env.docker.example .env.docker
```

Edit `.env.docker`, then start with:

```bash
docker compose --env-file .env.docker up -d --build
```

Docker overrides use `JUST_WE_*` variable names, such as
`JUST_WE_JWT_SECRET_KEY` and `JUST_WE_DEFAULT_ADMIN_PASSWORD`. The compose file
maps those values to the environment variable names consumed by the app. This
avoids accidentally reusing a local development `.env` file, which Docker
Compose reads automatically for interpolation.

The compose file intentionally uses internal container hostnames for
`DATABASE_URL` and `REDIS_URL` by default:

```text
postgresql+asyncpg://postgres:postgres@postgres:5432/dynamicwepubmonitor
redis://redis:6379/0
```

## Upgrade

```bash
git pull
docker compose build app
docker compose up -d
```

The app entrypoint initializes a completely empty database from the current
SQLAlchemy metadata, stamps it at the current Alembic head, and then runs
`alembic upgrade head` before starting Uvicorn. Non-empty databases go straight
through normal Alembic migrations.

## Logs and Health

```bash
docker compose ps
docker compose logs -f app
curl -fsS http://localhost:8000/health
```

The app healthcheck calls `/health` inside the container.

## Backup

Create a backup directory:

```bash
mkdir -p backups
```

Dump PostgreSQL:

```bash
docker compose exec -T postgres \
  pg_dump -U postgres dynamicwepubmonitor > backups/just-we.sql
```

Archive uploaded media:

```bash
docker run --rm \
  -v "$(basename "$PWD")_just-we-media:/media:ro" \
  -v "$PWD/backups:/backups" \
  alpine tar -czf /backups/just-we-media.tgz -C /media .
```

## Restore

Restore PostgreSQL into a running stack:

```bash
docker compose exec -T postgres \
  psql -U postgres dynamicwepubmonitor < backups/just-we.sql
```

Restore media:

```bash
docker run --rm \
  -v "$(basename "$PWD")_just-we-media:/media" \
  -v "$PWD/backups:/backups:ro" \
  alpine sh -c 'rm -rf /media/* && tar -xzf /backups/just-we-media.tgz -C /media'
```

## Stop and Reset

Stop containers while keeping data:

```bash
docker compose down
```

Stop and remove all Docker volumes:

```bash
docker compose down -v
```

## Static Web Serving

The Docker image builds `frontend/dist` and serves it from the FastAPI app.
Backend routes keep their existing behavior:

- `/api/*` is the API.
- `/docs`, `/redoc`, and `/openapi.json` are FastAPI documentation endpoints.
- `/media/*` serves localized media.
- Other paths fall back to `index.html`, so Vue deep links such as `/articles`
  and `/settings` can be refreshed directly.

## Build Context

`external_references/` is a local-only reference directory. It is ignored by Git
and excluded by `.dockerignore`, so it is not uploaded to GitHub and is not sent
to the Docker build context.
