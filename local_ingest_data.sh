#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_COMMAND="${RAGEVAL_PYTHON:-python3.12}"
VENV_DIR="$PROJECT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
REQUIREMENTS_MARKER="$VENV_DIR/.requirements-installed"

cd "$PROJECT_DIR"

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "Usage: ./local_ingest_data.sh [--model mini|bge|arctic|all] [--clean] [--yes]"
    echo
    echo "Runs ingestion natively on macOS using the Apple GPU through PyTorch MPS."
    echo "On first use, creates .venv with python3.12 and installs requirements.txt."
    echo "Set RAGEVAL_PYTHON to override the Python command used to create .venv."
    exit 0
fi

if [ ! -x "$VENV_PYTHON" ]; then
    if ! command -v "$PYTHON_COMMAND" >/dev/null 2>&1; then
        echo "Error: $PYTHON_COMMAND was not found."
        echo "Install it with: brew install python@3.12"
        exit 1
    fi

    echo "Creating native macOS virtual environment at $VENV_DIR..."
    "$PYTHON_COMMAND" -m venv "$VENV_DIR"
fi

if [ ! -f "$REQUIREMENTS_MARKER" ] || [ "$REQUIREMENTS_FILE" -nt "$REQUIREMENTS_MARKER" ]; then
    echo "Installing native macOS dependencies from requirements.txt..."
    "$VENV_PYTHON" -m pip install --upgrade pip
    "$VENV_PYTHON" -m pip install -r "$REQUIREMENTS_FILE"
    touch "$REQUIREMENTS_MARKER"
fi

"$VENV_PYTHON" - <<'PY'
import sys

import torch

if not torch.backends.mps.is_available():
    detail = (
        "this PyTorch build has no MPS support"
        if not torch.backends.mps.is_built()
        else "macOS or this Mac did not expose an MPS device"
    )
    print(f"Error: Apple GPU acceleration is unavailable: {detail}.", file=sys.stderr)
    sys.exit(1)

print(f"Apple GPU ready: {torch.backends.mps.get_name()}")
PY

INGEST_ARGS=()
for argument in "$@"; do
    if [ "$argument" = "--clean" ]; then
        INGEST_ARGS+=("--force-rebuild")
    else
        INGEST_ARGS+=("$argument")
    fi
done

RAGEVAL_DEVICE=mps exec "$VENV_PYTHON" scripts/ingest.py "${INGEST_ARGS[@]}"
