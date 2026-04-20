# Changelog

All notable changes to Just—We are tracked here.

## Unreleased

- Renamed the GitHub project and documentation branding to Just—We.
- Decoupled article fetching from AI analysis: fetched articles are saved first,
  then queued for background AI processing.
- Added AI text/image connectivity tests using dedicated synthetic payloads.
- Simplified proxy configuration around static residential login/list services
  and dynamic residential article/image services.
- Added Docker one-command deployment for app, PostgreSQL, and Redis.
- Added production SPA static serving from the FastAPI container.
- Added open source project files: license, contribution guide, security policy,
  code of conduct, GitHub templates, and CI workflow.
- Expanded deployment and configuration documentation.

## 0.1.0

- Consolidated the project around the current `collector_accounts`,
  `monitored_accounts`, article, Feed, export, proxy, rate-limit, and v2 admin UI
  workflows.
- Removed legacy account routes and unused v1 frontend resources.
