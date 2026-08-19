#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_DIR"

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "Usage: ./ingest_data.sh [--model mini|bge|arctic|all] [--clean] [--yes]"
    echo
    echo "Without options, source changes are processed and all missing model indexes are built."
    echo "--model MODEL  Build mini, bge, arctic, or all. Default: all."
    echo "--clean        Confirm before replacing generated indexes and metadata storage."
    echo "--yes          Skip the clean confirmation. Intended for explicit automation."
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
