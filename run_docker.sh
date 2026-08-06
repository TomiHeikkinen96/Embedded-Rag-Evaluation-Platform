#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -eq 0 ]; then
  echo "Usage: ./run_docker.bash <python-file> [arguments...]" >&2
  echo "Example: ./run_docker.bash search_index.py \"maximum current\"" >&2
  exit 2
fi

cd "$PROJECT_DIR"
docker compose run --rm rag python "$@"
