#!/usr/bin/env bash
# Stop the API, web app and containers. Database data is kept.
# Usage: ./scripts/dev-down.sh          Add --quit-docker to also quit Docker Desktop (macOS).
set -uo pipefail
cd "$(dirname "$0")/.."

for name in api web; do
  if [ -f ".dev/$name.pid" ]; then
    pkill -P "$(cat .dev/$name.pid)" 2>/dev/null
    kill "$(cat .dev/$name.pid)" 2>/dev/null
    rm -f ".dev/$name.pid"
  fi
done
# Anything still holding the dev ports
lsof -ti:3000,8000 | xargs kill 2>/dev/null
echo "API and web stopped."

if docker info >/dev/null 2>&1; then
  docker compose stop
  echo "Containers stopped. Data is kept (never use 'down -v' unless you want to wipe it)."
fi

if [ "${1:-}" = "--quit-docker" ] && [ "$(uname)" = "Darwin" ]; then
  osascript -e 'quit app "Docker"' 2>/dev/null && echo "Docker Desktop quit."
fi
