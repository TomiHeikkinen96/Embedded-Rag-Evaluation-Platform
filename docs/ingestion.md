# Ingestion

## Normal behaviour

Run:

```bash
./ingest_data.sh
```

On Apple Silicon macOS, the equivalent GPU-backed command is:

```bash
./local_ingest_data.sh
```

It shares `data/` and `storage/` with Docker, so use only one ingestion process
at a time. The generated normalized embeddings and FAISS metadata retain the
same format regardless of whether CPU or MPS produced them.

The current file tracker stores absolute source paths. Docker sees a document
as `/app/data/...`, while native macOS sees its host path. Switching between
the two ingestion runtimes therefore causes one complete chunk and index
rebuild even when the PDF contents are unchanged. Pick one ingestion runtime
for routine use; search and inspection tools can still read the resulting
shared storage from Docker.

The ingestion path hashes PDFs under `data/`, compares them with the local
file-tracking database, and ensures the requested model indexes exist.

- New, changed, restored, and deleted documents update the shared chunk set.
- A source change invalidates every model index so comparisons cannot use
  different chunk corpora.
- Unchanged PDFs are not parsed again.
- Missing requested indexes are built from the stored shared chunks.
- Current requested indexes are skipped.

Without selectors, all three registered model indexes are made current. Use
`mini`, `bge`, or `arctic` to build only one index:

```bash
./ingest_data.sh --model all
./ingest_data.sh --model bge
```

A complete explorer requires all three.

Each model build reports model-loading time, embedding time and throughput,
FAISS/metadata write time, and total elapsed time. Loading time includes any
first-run model download, so compare warm-cache runs separately from first use.

## Clean rebuild

Run:

```bash
./ingest_data.sh --clean
```

Clean mode asks before removing generated FAISS indexes and SQLite state. If
the confirmation is declined, existing storage is left unchanged. Automation
may explicitly add `--yes`:

```bash
./ingest_data.sh --clean --yes
```

Clean rebuilds are useful after incompatible schema, embedding-model, or
indexing changes. They should not be the default workflow.

## Chunk preparation

The current PDF chunker:

- removes known repeated PDF furniture
- groups prose around sentence boundaries
- applies limited sentence overlap
- detects table/list-like blocks
- attaches nearby heading and table-header context to structured row groups
- rejects several low-information fragments

This is a practical heuristic baseline, not layout-aware PDF understanding.
Tables remain the most difficult source format and are a major target of the
planned chunker comparison.

## Stored metadata

One SQLite database records the shared chunk corpus, source location, retrieval
text, larger display context, model/index configurations, and explicit vector
mappings. Chunk metadata is intentionally not copied into one database per
model. Each model has its own normalized FAISS artifact:

```text
storage/indexes/custom/mini.faiss
storage/indexes/custom/bge.faiss
storage/indexes/custom/arctic.faiss
```

SQLite maps `(index_id, vector_id)` to a chunk, so the same numeric vector id
can safely exist in every model index.

## Model registry

- `mini`: `sentence-transformers/all-MiniLM-L6-v2`, fast 384-dimensional baseline
- `bge`: `BAAI/bge-base-en-v1.5`, 768-dimensional retrieval model
- `arctic`: `Snowflake/snowflake-arctic-embed-m-v1.5`, 768-dimensional retrieval-focused candidate

BGE and Arctic receive their retrieval instruction on queries, not documents.
Arctic uses the standard Sentence Transformers loading path without remote
model code. Dependency versions remain pinned so clean rebuilds use the same
local software stack.

See [retrieval pipeline](retrieval-pipeline.md) for how those artifacts are used
during search.
