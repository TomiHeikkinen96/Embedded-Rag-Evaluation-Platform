#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8000}"
SERVER_CONTAINER_NAME="rageval-evaluation-server"
SERVER_CONTAINER_ROLE="evaluation-server"
SERVER_PID=""

cd "$PROJECT_DIR"

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required to check when the evaluation server is ready." >&2
  exit 1
fi

remove_existing_evaluation_server() {
  if ! docker container inspect "$SERVER_CONTAINER_NAME" >/dev/null 2>&1; then
    return
  fi

  local existing_role
  existing_role="$(
    docker container inspect \
      --format '{{ index .Config.Labels "com.rageval.role" }}' \
      "$SERVER_CONTAINER_NAME"
  )"
  if [ "$existing_role" != "$SERVER_CONTAINER_ROLE" ]; then
    echo "Error: container $SERVER_CONTAINER_NAME exists but is not a RAGeval evaluation server." >&2
    echo "Refusing to remove an unrelated container." >&2
    exit 1
  fi

  echo "Stopping previous RAGeval evaluation server..."
  docker container rm --force "$SERVER_CONTAINER_NAME" >/dev/null
}

cleanup_server() {
  local existing_role
  existing_role="$(
    docker container inspect \
      --format '{{ index .Config.Labels "com.rageval.role" }}' \
      "$SERVER_CONTAINER_NAME" 2>/dev/null || true
  )"
  if [ "$existing_role" = "$SERVER_CONTAINER_ROLE" ]; then
    docker container rm --force "$SERVER_CONTAINER_NAME" >/dev/null 2>&1 || true
  fi
  if [ -n "$SERVER_PID" ]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}

trap cleanup_server EXIT
trap 'exit 130' INT TERM

remove_existing_evaluation_server

URL="http://localhost:${PORT}"
if command -v nc >/dev/null 2>&1; then
  PORT_IN_USE_COMMAND=(nc -z 127.0.0.1 "$PORT")
else
  PORT_IN_USE_COMMAND=(curl --silent --output /dev/null --max-time 1 "$URL")
fi
if "${PORT_IN_USE_COMMAND[@]}" >/dev/null 2>&1; then
  echo "Error: port $PORT is already used by something other than the managed RAGeval server." >&2
  echo "Choose another port, for example: ./view_evaluation.sh 8080" >&2
  exit 1
fi

echo "Generating visualization data from all registered model indexes..."
docker compose run --rm rag python scripts/visualization/generate_embedding_data.py
echo "Comparing retrieved results with the golden benchmark..."
docker compose run --rm rag python scripts/visualization/generate_golden_evaluation.py
echo "Exporting saved generation-evaluation runs..."
mkdir -p "$PROJECT_DIR/runs/generation"
docker compose run --rm rag python scripts/visualization/generate_generation_evaluation.py

docker compose run --rm \
  --name "$SERVER_CONTAINER_NAME" \
  --label "com.rageval.role=$SERVER_CONTAINER_ROLE" \
  --publish "127.0.0.1:${PORT}:8000" \
  --volume "$PROJECT_DIR/visualization:/app/visualization:ro" \
  rag python -m http.server 8000 --directory /app/visualization &
SERVER_PID=$!

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
