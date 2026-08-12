#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_DIR"

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "Usage: ./ingest_data.sh [--model mini|bge|arctic|all] [--clean] [--yes]"
    echo
    echo "Without options, source changes are processed and all missing model indexes are built."
    echo "--model selects one registered embedding model; all is the default."
    echo "--clean confirms before replacing generated indexes and metadata storage."
    exit 0
fi

INGEST_ARGS=()
for argument in "$@"; do
  if [ "$argument" = "--clean" ]; then
    INGEST_ARGS+=("--force-rebuild")
  else
    INGEST_ARGS+=("$argument")
  fi
done

if [ "${#INGEST_ARGS[@]}" -eq 0 ]; then
  docker compose run --rm rag python scripts/ingest.py
else
  docker compose run --rm rag python scripts/ingest.py "${INGEST_ARGS[@]}"
fi
