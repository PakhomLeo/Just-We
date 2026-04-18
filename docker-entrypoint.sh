#!/usr/bin/env bash
set -euo pipefail

wait_for_url() {
  local name="$1"
  local url="$2"
  local default_port="$3"

  python - "$name" "$url" "$default_port" <<'PY'
import socket
import sys
import time
from urllib.parse import urlparse

name, raw_url, default_port = sys.argv[1], sys.argv[2], int(sys.argv[3])
parsed = urlparse(raw_url)
host = parsed.hostname
port = parsed.port or default_port

if not host:
    raise SystemExit(f"{name} URL is missing a host: {raw_url}")

for attempt in range(1, 61):
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"{name} is reachable at {host}:{port}")
            break
    except OSError as exc:
        if attempt == 60:
            raise SystemExit(f"Timed out waiting for {name} at {host}:{port}: {exc}")
        print(f"Waiting for {name} at {host}:{port} ({attempt}/60)")
        time.sleep(1)
PY
}

wait_for_url "PostgreSQL" "${DATABASE_URL}" "5432"
wait_for_url "Redis" "${REDIS_URL}" "6379"

python -m app.utils.bootstrap_fresh_db
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
