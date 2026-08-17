#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$PROJECT_DIR/visualization"
SNAPSHOT_ROOT="$PROJECT_DIR/backups/evaluation-demo"
SNAPSHOT_ID="$(date -u +'%Y-%m-%dT%H-%M-%SZ')"
SNAPSHOT_DIR="$SNAPSHOT_ROOT/$SNAPSHOT_ID"
BUILD_DIR=""
PLOTLY_URL="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@3.1.0/plotly.min.js"

required_files=(
  "index.html"
  "embedding-data.json"
  "golden-evaluation.json"
  "generation-evaluation.json"
)

for file_name in "${required_files[@]}"; do
  if [ ! -s "$SOURCE_DIR/$file_name" ]; then
    echo "Error: $SOURCE_DIR/$file_name is missing or empty." >&2
    echo "Run ./view_evaluation.sh once to export the current evaluation data." >&2
    exit 1
  fi
done

mkdir -p "$SNAPSHOT_ROOT"
BUILD_DIR="$(mktemp -d "$SNAPSHOT_ROOT/.building.XXXXXX")"

cleanup_build() {
  if [ -n "$BUILD_DIR" ] && [ -d "$BUILD_DIR" ]; then
    rm -rf "$BUILD_DIR"
  fi
}
trap cleanup_build EXIT

echo "Freezing the current evaluation explorer..."
cp "$SOURCE_DIR/embedding-data.json" "$BUILD_DIR/embedding-data.json"
cp "$SOURCE_DIR/golden-evaluation.json" "$BUILD_DIR/golden-evaluation.json"
cp "$SOURCE_DIR/generation-evaluation.json" "$BUILD_DIR/generation-evaluation.json"

PREVIOUS_PLOTLY="$({
  find "$SNAPSHOT_ROOT" -mindepth 2 -maxdepth 2 -type f -name 'plotly.min.js' 2>/dev/null || true
} | sort | tail -n 1)"
if [ -n "$PREVIOUS_PLOTLY" ] && [ -s "$PREVIOUS_PLOTLY" ]; then
  echo "Reusing the bundled offline Plotly asset..."
  cp "$PREVIOUS_PLOTLY" "$BUILD_DIR/plotly.min.js"
else
  echo "Downloading Plotly once for offline use..."
  curl --fail --location --silent --show-error \
    --output "$BUILD_DIR/plotly.min.js" \
    "$PLOTLY_URL"
fi

sed \
  's#https://cdn.jsdelivr.net/npm/plotly.js-dist-min@3.1.0/plotly.min.js#./plotly.min.js#' \
  "$SOURCE_DIR/index.html" > "$BUILD_DIR/index.html"

{
  echo "snapshot_id=$SNAPSHOT_ID"
  echo "created_at_utc=$SNAPSHOT_ID"
  echo "source_directory=$SOURCE_DIR"
  echo "contents=index.html,plotly.min.js,embedding-data.json,golden-evaluation.json,generation-evaluation.json"
} > "$BUILD_DIR/snapshot-info.txt"

if [ -e "$SNAPSHOT_DIR" ]; then
  echo "Error: snapshot already exists: $SNAPSHOT_DIR" >&2
  exit 1
fi

mv "$BUILD_DIR" "$SNAPSHOT_DIR"
BUILD_DIR=""

echo "Created frozen evaluation snapshot:"
echo "  $SNAPSHOT_DIR"
echo "Open it later with: ./backup_view_evaluation.sh"
