#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -eq 0 ]; then
  echo "Usage: ./run_script.sh <python-script> [arguments...]" >&2
  echo "Example: ./run_script.sh search_index.py \"maximum current\"" >&2
  exit 2
fi

SCRIPT_FILE="$1"
shift

if [[ "$SCRIPT_FILE" != scripts/* ]]; then
  SCRIPT_FILE="scripts/$SCRIPT_FILE"
fi

if [ ! -f "$PROJECT_DIR/$SCRIPT_FILE" ]; then
  echo "Error: script not found: $SCRIPT_FILE" >&2
  exit 2
fi

cd "$PROJECT_DIR"
docker compose run --rm rag python "$SCRIPT_FILE" "$@"
