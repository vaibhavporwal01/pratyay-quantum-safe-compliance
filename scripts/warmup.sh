#!/usr/bin/env bash
# Wake the API and database before a review. Usage: ./scripts/warmup.sh https://your-api.onrender.com
API=${1:?usage: warmup.sh <api-url>}
for i in 1 2 3 4 5 6; do
  if curl -fsS --max-time 90 "$API/health/db"; then echo; echo "API and DB are up"; exit 0; fi
  echo "waking... ($i)"; sleep 15
done
echo "still down: check the Render and Neon dashboards"; exit 1
