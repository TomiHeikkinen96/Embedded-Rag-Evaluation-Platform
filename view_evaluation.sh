#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8000}"

cd "$PROJECT_DIR"

echo "Generating visualization data from the active FAISS index..."
docker compose run --rm rag python scripts/visualization/generate_embedding_data.py

URL="http://localhost:${PORT}"
echo "Evaluation explorer: $URL"
echo "Press Ctrl+C to stop the local server."

docker compose run --rm \
  --publish "127.0.0.1:${PORT}:8000" \
  --volume "$PROJECT_DIR/visualization:/app/visualization:ro" \
  rag python -m http.server 8000 --directory /app/visualization &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT INT TERM

if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
fi

wait "$SERVER_PID"
