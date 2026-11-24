#!/usr/bin/env bash
# Start everything for local development: database, API and web app.
# Usage: ./scripts/dev-up.sh        Logs: .dev/api.log and .dev/web.log
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .dev

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Open Docker Desktop, wait until it is running, then try again."
  exit 1
fi

echo "Starting Postgres and Mailpit..."
docker compose up -d
for i in $(seq 1 30); do
  docker compose exec -T db pg_isready -U pratyay >/dev/null 2>&1 && break
  sleep 1
done

echo "Applying migrations..."
(cd apps/api && uv run alembic upgrade head)

if lsof -ti:8000 >/dev/null 2>&1; then
  echo "API already running on :8000"
else
  (cd apps/api && nohup uv run fastapi dev app/main.py > ../../.dev/api.log 2>&1 & echo $! > ../../.dev/api.pid)
  echo "API starting on http://localhost:8000 (logs: .dev/api.log)"
fi

if lsof -ti:3000 >/dev/null 2>&1; then
  echo "Web already running on :3000"
else
  (cd apps/web && nohup pnpm dev > ../../.dev/web.log 2>&1 & echo $! > ../../.dev/web.pid)
  echo "Web starting on http://localhost:3000 (logs: .dev/web.log)"
fi

sleep 4
curl -fsS --max-time 10 http://localhost:8000/health/db >/dev/null 2>&1 \
  && echo "Ready: API and database are up." \
  || echo "API still starting. Check: tail -f .dev/api.log"
