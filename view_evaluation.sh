#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8000}"

cd "$PROJECT_DIR"

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required to check when the evaluation server is ready." >&2
  exit 1
fi

echo "Generating visualization data from all registered model indexes..."
docker compose run --rm rag python scripts/visualization/generate_embedding_data.py
echo "Comparing retrieved results with the golden benchmark..."
docker compose run --rm rag python scripts/visualization/generate_golden_evaluation.py

URL="http://localhost:${PORT}"
docker compose run --rm \
  --publish "127.0.0.1:${PORT}:8000" \
  --volume "$PROJECT_DIR/visualization:/app/visualization:ro" \
  rag python -m http.server 8000 --directory /app/visualization &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT INT TERM

echo "Waiting for the local server..."
SERVER_READY=0
for _ in {1..300}; do
  if curl --fail --silent --output /dev/null "$URL"; then
    SERVER_READY=1
    break
  fi

  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Error: evaluation server stopped before it became ready." >&2
    wait "$SERVER_PID"
    exit 1
  fi

  sleep 0.1
done

if [ "$SERVER_READY" -ne 1 ]; then
  echo "Error: evaluation server was not ready at $URL after 30 seconds." >&2
  exit 1
fi

echo "Evaluation explorer: $URL"
echo "Press Ctrl+C to stop the local server."

if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
fi

wait "$SERVER_PID"
