#!/usr/bin/env bash
# Stop the API, web app and containers. Database data is kept.
# Usage: ./scripts/dev-down.sh               stop app processes and containers
#        ./scripts/dev-down.sh --quit-docker also shut Docker Desktop down cleanly (macOS)
set -uo pipefail
cd "$(dirname "$0")/.."

# 1. App processes
for name in api web; do
  if [ -f ".dev/$name.pid" ]; then
    pid="$(cat .dev/$name.pid)"
    pkill -TERM -P "$pid" 2>/dev/null
    kill -TERM "$pid" 2>/dev/null
    rm -f ".dev/$name.pid"
  fi
done
pids="$(lsof -ti:3000,8000 2>/dev/null)"
[ -n "$pids" ] && kill -TERM $pids 2>/dev/null
echo "API and web stopped."

# 2. Containers: stop gracefully and wait until nothing is running
if docker info >/dev/null 2>&1; then
  docker compose stop --timeout 20
  for i in $(seq 1 30); do
    [ -z "$(docker compose ps -q --status running 2>/dev/null)" ] && break
    sleep 1
  done
  echo "Containers stopped. Data is kept in the pgdata volume."
else
  echo "Docker is not running; nothing to stop."
fi

# 3. Optional: shut Docker Desktop down cleanly
if [ "${1:-}" = "--quit-docker" ] && [ "$(uname)" = "Darwin" ]; then
  if docker info >/dev/null 2>&1; then
    sleep 3   # let the VM settle after the containers stop
    if docker desktop stop >/dev/null 2>&1; then
      echo "Docker Desktop stopped."
    else
      # Older Docker Desktop without the 'docker desktop' command: ask the app to quit normally
      osascript -e 'tell application "Docker Desktop" to quit' 2>/dev/null \
        || osascript -e 'tell application "Docker" to quit' 2>/dev/null
      echo "Asked Docker Desktop to quit."
    fi
  fi
fi
