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

## Command defaults at a glance

The root shell files are thin environment wrappers. They locate the repository,
select Docker or the native Python environment, and forward arguments to the
Python entry point. Retrieval, generation, and evaluation behaviour remains in
the Python modules and committed experiment specification.

| Command | Default with no optional arguments | Important selectors |
| --- | --- | --- |
| `./ingest_data.sh` | Incremental Docker ingestion; ensure all `mini`, `bge`, and `arctic` indexes | `--model`, `--clean`, `--yes` |
| `./local_ingest_data.sh` | Same ingestion selection using native Apple MPS | `--model`, `--clean`, `--yes`; `RAGEVAL_PYTHON` selects the environment-creation executable |
| `./run_script.sh SCRIPT` | Run one `scripts/` Python entry point in Docker | Every later argument is forwarded to that script |
| `./ask_question.sh QUESTION` | Arctic retrieval, top 3, `rageval-qwen`, streaming, local Ollama URL | `--embedding`, `--top-k`, `--model`, `--show-context`, `--no-stream`, `--url` |
| `./run_generation_eval.sh` | Run the complete committed canonical experiment | `--condition`, `--case`, `--repetitions`, `--top-k`, `--model`, `--benchmark-dir`, `--url` |
| `./view_evaluation.sh` | Regenerate current reports and serve them on port `8000` | Optional positional port |
| `./create_snapshot_from_current_eval.sh` | Freeze the currently exported explorer into a timestamped offline snapshot | No options |
| `./backup_view_evaluation.sh` | Serve the newest frozen snapshot on port `8000` and open it | Optional positional port; `RAGEVAL_NO_OPEN=1` suppresses browser opening |

Use `--help` on the ingestion wrappers and Python-backed commands for the
executable option descriptions. For a Docker tool, pass help through the generic
wrapper, for example `./run_script.sh search_index.py --help`.

## Model-selection rule

Each embedding alias has its own FAISS index. A consumer can only select an
index that ingestion has built. The defaults intentionally differ by task:

- ingestion uses `all`, producing every registered index;
- `search_index.py`, `benchmark_search.py`, and model-specific database
  inspection default to the fast `mini` baseline;
- `ask_question.sh` defaults to the current grounded-generation path,
  `arctic`.

Therefore the no-option ingestion command supports every downstream default.
If you intentionally ingest only one model, select the same alias later:

```bash
# Build only BGE.
./local_ingest_data.sh --model bge

# Use the BGE index for a grounded answer.
./ask_question.sh --embedding bge "question"

# Use the BGE index for retrieval-only inspection in Docker.
./run_script.sh search_index.py --model bge "question"
```

## Ingestion commands

```bash
# Default: incremental update and all registered model indexes.
./ingest_data.sh

# Default for --model: all. Choices: mini, bge, arctic, all.
./ingest_data.sh --model bge

# Default: preserve generated storage. --clean asks before replacing it.
./ingest_data.sh --clean

# Skip the clean confirmation only in deliberate automation.
./ingest_data.sh --clean --yes

# Default port: 8000.
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
# Default: all models, incremental ingestion, RAGEVAL_DEVICE=mps.
./local_ingest_data.sh

# Build only BGE.
./local_ingest_data.sh --model bge

# Clean rebuild with confirmation.
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

## Grounded question command

The native question wrapper requires the `.venv` created by
`local_ingest_data.sh` and a running Ollama service:

```bash
# Defaults: --embedding arctic --model rageval-qwen --top-k 3, streaming on,
# and Ollama at http://localhost:11434/api/chat.
./ask_question.sh "question"

# Select another index that has already been built.
./ask_question.sh --embedding mini "question"

# Inspect the exact retrieved excerpts and increase retrieval depth.
./ask_question.sh --show-context --top-k 10 "question"

# Wait for one complete response instead of streaming it.
./ask_question.sh --no-stream "question"

# Show all options and their current executable defaults.
./ask_question.sh --help
```

`--model` selects the Ollama generation model and `--embedding` selects the
retrieval index; they are independent choices.

## Generation evaluation commands

```bash
# Default: every case and condition from the committed experiment specification.
./run_generation_eval.sh

# Repeat --case or --condition to select several. Filtered runs are non-canonical.
./run_generation_eval.sh --case flash-voltage-regulator --condition oracle

# Defaults come from experiment.json; an override is recorded as non-canonical.
./run_generation_eval.sh --condition dense_rag:arctic --top-k 10

# Show the full evaluator interface.
./run_generation_eval.sh --help
```

The canonical model, conditions, top-k, repetitions, prompt version, timeout,
and context limits live in
[`benchmarks/esp32-generation-v1/experiment.json`](../benchmarks/esp32-generation-v1/experiment.json),
so a baseline run is reproducible without duplicating those values in shell.

## Explorer and frozen snapshot commands

```bash
# Default port: 8000. Regenerates data, starts a managed Docker server, opens it.
./view_evaluation.sh
./view_evaluation.sh 8080

# No options: copy the current exported data and bundle Plotly for offline use.
./create_snapshot_from_current_eval.sh

# Default: newest snapshot, port 8000, browser opening enabled.
./backup_view_evaluation.sh
RAGEVAL_NO_OPEN=1 ./backup_view_evaluation.sh 8080
```

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
