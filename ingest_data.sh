#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_DIR"

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "Usage: ./ingest_data.sh [--clean] [--yes]"
    echo
    echo "Without options, only new, changed, restored, or deleted PDFs are processed."
    echo "--clean confirms before replacing generated index and metadata storage."
    exit 0
fi

if [ "${1:-}" = "--clean" ]; then
  shift
  docker compose run --rm rag python scripts/ingest.py --force-rebuild "$@"
else
  docker compose run --rm rag python scripts/ingest.py "$@"
fi
