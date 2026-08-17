#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SNAPSHOT_ROOT="$PROJECT_DIR/backups/evaluation-demo"
PORT="${1:-8000}"
SERVER_PID=""

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
  echo "Error: port must be an integer from 1 to 65535." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required to serve the frozen evaluation snapshot." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required to check when the backup server is ready." >&2
  exit 1
fi

SNAPSHOT_DIR="$({
  find "$SNAPSHOT_ROOT" -mindepth 1 -maxdepth 1 -type d -name '20*' 2>/dev/null || true
} | sort | tail -n 1)"

if [ -z "$SNAPSHOT_DIR" ]; then
  echo "Error: no frozen evaluation snapshot exists." >&2
  echo "Create one from the current exported data with: ./create_snapshot_from_current_eval.sh" >&2
  exit 1
fi

required_files=(
  "index.html"
  "plotly.min.js"
  "embedding-data.json"
  "golden-evaluation.json"
  "generation-evaluation.json"
)
for file_name in "${required_files[@]}"; do
  if [ ! -s "$SNAPSHOT_DIR/$file_name" ]; then
    echo "Error: frozen snapshot is incomplete: $SNAPSHOT_DIR/$file_name" >&2
    exit 1
  fi
done

URL="http://127.0.0.1:${PORT}"
if command -v nc >/dev/null 2>&1; then
  PORT_IN_USE_COMMAND=(nc -z 127.0.0.1 "$PORT")
else
  PORT_IN_USE_COMMAND=(curl --silent --output /dev/null --max-time 1 "$URL")
fi
if "${PORT_IN_USE_COMMAND[@]}" >/dev/null 2>&1; then
  echo "Error: port $PORT is already in use." >&2
  echo "Choose another port, for example: ./backup_view_evaluation.sh 8080" >&2
  exit 1
fi

cleanup_server() {
  if [ -n "$SERVER_PID" ]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup_server EXIT
trap 'exit 130' INT TERM

python3 -m http.server "$PORT" \
  --bind 127.0.0.1 \
  --directory "$SNAPSHOT_DIR" &
SERVER_PID=$!

echo "Waiting for the frozen evaluation server..."
SERVER_READY=0
for _ in {1..100}; do
  if curl --fail --silent --output /dev/null "$URL"; then
    SERVER_READY=1
    break
  fi

  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Error: backup evaluation server stopped before it became ready." >&2
    wait "$SERVER_PID"
    exit 1
  fi

  sleep 0.1
done

if [ "$SERVER_READY" -ne 1 ]; then
  echo "Error: backup evaluation server was not ready at $URL after 10 seconds." >&2
  exit 1
fi

echo "Frozen evaluation snapshot: $(basename "$SNAPSHOT_DIR")"
echo "Evaluation explorer: $URL"
echo "Press Ctrl+C to stop the local server."

if [ "${RAGEVAL_NO_OPEN:-0}" != "1" ]; then
  if command -v open >/dev/null 2>&1; then
    open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true
  fi
fi

wait "$SERVER_PID"
