#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-us-market-morning}"
CONTAINER_NAME="${CONTAINER_NAME:-us-market-morning}"
START_PORT="${PORT:-8000}"
PORT_TO_USE="$START_PORT"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

while lsof -iTCP:"$PORT_TO_USE" -sTCP:LISTEN >/dev/null 2>&1; do
  PORT_TO_USE=$((PORT_TO_USE + 1))
done

mkdir -p data/reports
docker build -t "$IMAGE_NAME" .
docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  --env-file .env \
  -e PORT=8000 \
  -p "$PORT_TO_USE:8000" \
  -v "$(pwd)/data:/app/data" \
  "$IMAGE_NAME"

echo "USMarketMorning is running at http://127.0.0.1:$PORT_TO_USE"
