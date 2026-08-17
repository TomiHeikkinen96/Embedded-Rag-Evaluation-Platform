#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "Error: native Python environment not found at $VENV_PYTHON" >&2
    echo "Create it and the Arctic index with: ./local_ingest_data.sh --model arctic" >&2
    exit 1
fi

cd "$PROJECT_DIR"
export RAGEVAL_DEVICE="${RAGEVAL_DEVICE:-mps}"
exec "$VENV_PYTHON" scripts/run_generation_eval.py "$@"
