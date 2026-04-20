# Contributing to Just—We

Thanks for helping improve Just—We. This project keeps a pragmatic review bar:
changes should be easy to run, covered by focused tests, and aligned with the
existing FastAPI service and Vue v2 admin UI.

## Development Setup

1. Install Python 3.12+, Node.js 20.19+ or 22.12+, PostgreSQL, and Redis.
2. Copy `.env.example` to `.env` and adjust local connection strings.
3. Install backend dependencies:

   ```bash
   uv sync
   ```

4. Install frontend dependencies:

   ```bash
   cd frontend
   npm install
   ```

5. Apply database migrations:

   ```bash
   uv run alembic upgrade head
   ```

## Quality Checks

Run these before opening a pull request:

```bash
uv run ruff check app tests scripts
uv run pytest -q
uv run python -m compileall app tests scripts
cd frontend && npm run build
```

For Docker changes, also run:

```bash
docker compose config
docker compose build
```

## Pull Request Guidelines

- Keep changes scoped to one behavior or one cleanup theme.
- Include tests for backend behavior, permissions, migrations, Feed/export, or
  scheduler changes.
- Keep generated runtime data out of the repository. Do not commit `.env`,
  `media/`, `logs/`, `frontend/dist/`, or `external_references/`.
- Document any new environment variable in `.env.example` and
  `docs/configuration.md`.
- Avoid broad rewrites unless they remove live risk or old unreachable code.

## Commit Style

Use short imperative commit messages, for example:

```text
Add Docker one-command deployment
Fix article export ownership filtering
Remove legacy account routes
```
