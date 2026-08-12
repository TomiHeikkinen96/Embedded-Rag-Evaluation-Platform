# Local Workflow

## Requirements

- Docker-compatible runtime
- Colima on the current Apple Silicon macOS setup
- Bash for the convenience wrappers
- `curl` for the evaluation-server readiness check

The Python tools run inside the container. Windows users can use Docker Desktop
and invoke the underlying Compose/Python commands; the shell wrappers are
conveniences rather than the only program interface.

## First setup

```bash
colima start
docker compose build
```

Rebuild the image after changing `Dockerfile` or `requirements.txt`. Python
source under `scripts/` is bind-mounted, so ordinary code edits do not require
an image rebuild.

## High-level commands

```bash
# Incremental ingestion
./ingest_data.sh

# Clean rebuild with confirmation
./ingest_data.sh --clean

# Generate and open the evaluation explorer
./view_evaluation.sh
./view_evaluation.sh 8080
```

`view_evaluation.sh` waits for the local server to answer before opening the
browser. Stop it with `Ctrl+C`.

## Individual tools

`run_script.sh` executes a Python entry point from `scripts/` in the same Docker
environment:

```bash
./run_script.sh search_index.py "maximum current" "ADC pins"
./run_script.sh benchmark_search.py --top-k 3
./run_script.sh db_inspect.py stats
./run_script.sh db_inspect.py index-status
./run_script.sh db_inspect.py index-integrity
```

The wrappers resolve the project directory themselves and can be invoked from a
different working directory.

## Local files

- Put source PDFs under `data/`.
- Generated FAISS and SQLite files appear under `storage/`.
- Downloaded Hugging Face models persist in the Compose volume.
- Generated explorer data appears as `visualization/embedding-data.json`.

These local artifacts are ignored by Git.

## Stopping the runtime

```bash
colima stop
```
