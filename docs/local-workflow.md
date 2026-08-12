# Local Workflow

## Requirements

- Docker-compatible runtime
- Colima on the current Apple Silicon macOS setup
- Bash for the convenience wrappers
- `curl` for the evaluation-server readiness check

The Python tools run inside the container. Windows users can use Docker Desktop
and invoke the underlying Compose/Python commands; the shell wrappers are
conveniences rather than the only program interface.

Native Apple GPU ingestion is an optional parallel macOS workflow. It requires
Homebrew Python 3.12 and does not replace the Docker workflow.

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
# Update chunks and build all missing model indexes
./ingest_data.sh

# Build one model-specific index
./ingest_data.sh --model bge

# Clean rebuild with confirmation
./ingest_data.sh --clean

# Generate and open the evaluation explorer
./view_evaluation.sh
./view_evaluation.sh 8080
```

`view_evaluation.sh` waits for the local server to answer before opening the
browser. Stop it with `Ctrl+C`.

## Native Apple GPU ingestion

Install the versioned Python formula once:

```bash
brew update
brew install python@3.12
python3.12 --version
```

Then run ingestion without starting Colima:

```bash
./local_ingest_data.sh
./local_ingest_data.sh --model bge
./local_ingest_data.sh --clean
```

On first use, `local_ingest_data.sh` creates `.venv`, installs
`requirements.txt`, and verifies that PyTorch exposes the Apple GPU through
MPS. Later runs reuse that environment. If `requirements.txt` changes, the
wrapper updates the environment before ingestion. Set `RAGEVAL_PYTHON` only if
the versioned executable has a nonstandard name or path.

The repository intentionally uses one requirements file. Native ingestion uses
PDF loading, chunking, PyTorch/Sentence Transformers, NumPy, and FAISS, so a
second reduced list would duplicate nearly the entire dependency set and could
drift from Docker. On macOS, pip selects the native PyTorch wheel with MPS;
Docker explicitly installs the Linux CPU wheel first.

## Individual tools

`run_script.sh` executes a Python entry point from `scripts/` in the same Docker
environment:

```bash
./run_script.sh search_index.py "maximum current" "ADC pins"
./run_script.sh search_index.py --model arctic "gpio matrix"
./run_script.sh benchmark_search.py --top-k 3
./run_script.sh benchmark_search.py --model bge --top-k 3
./run_script.sh db_inspect.py stats
./run_script.sh db_inspect.py index-status
./run_script.sh db_inspect.py --model arctic index-integrity
```

The wrappers resolve the project directory themselves and can be invoked from a
different working directory.

## Local files

- Put source PDFs under `data/`.
- The shared SQLite database appears under `storage/`; model FAISS files appear
  under `storage/indexes/custom/`.
- Downloaded Hugging Face models persist in the Compose volume.
- Generated explorer data appears as `visualization/embedding-data.json`.

These local artifacts are ignored by Git.

## Stopping the runtime

```bash
colima stop
```
