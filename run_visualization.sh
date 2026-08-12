#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8000}"

cd "$PROJECT_DIR"

echo "Generating visualization data from the active FAISS index..."
docker compose run --rm --build \
  --volume "$PROJECT_DIR/visualization:/output" \
  rag python visualization/generate_embedding_data.py \
  --output /output/embedding-data.json

URL="http://localhost:${PORT}"
echo "Embedding lab: $URL"
echo "Press Ctrl+C to stop the local server."

python3 -m http.server "$PORT" --directory "$PROJECT_DIR/visualization" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT INT TERM

if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
fi

wait "$SERVER_PID"
