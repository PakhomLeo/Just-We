# Security Policy

## Supported Versions

Security fixes target the current `main` branch. This project does not maintain
older release branches yet.

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability.

Report privately by contacting the repository owner on GitHub or by opening a
private security advisory if the repository has advisories enabled. Include:

- Affected version or commit.
- Impacted component, such as authentication, Feed token, export download,
  proxy handling, or media serving.
- Reproduction steps and expected impact.
- Whether the issue requires valid credentials.

We aim to acknowledge reports within 72 hours and publish a fix or mitigation
once the risk is understood.

## Deployment Notes

- Change `JWT_SECRET_KEY` before exposing the service.
- Change the default admin password or disable default admin bootstrap after
  first setup.
- Treat `.env`, AI keys, proxy credentials, QR sessions, media files, and
  database backups as sensitive.
- Do not expose Postgres or Redis directly to the public Internet.
