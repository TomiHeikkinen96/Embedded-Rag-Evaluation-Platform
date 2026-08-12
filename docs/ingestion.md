# Ingestion

## Normal behaviour

Run:

```bash
./ingest_data.sh
```

The ingestion path hashes PDFs under `data/` and compares them with the local
file-tracking database.

- New documents are loaded, chunked, embedded, and added.
- Changed documents have their old chunks and vectors replaced.
- Restored documents are added again.
- Deleted documents have their chunks and vectors removed.
- Unchanged documents are skipped.

This is the normal development workflow. It preserves the current index and
avoids re-embedding the full corpus after every small change.

## Clean rebuild

Run:

```bash
./ingest_data.sh --clean
```

Clean mode asks before removing the generated FAISS index and SQLite state. If
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

SQLite records source location, retrieval text, larger display context,
embedding model, and the explicit vector mapping. The FAISS file stores the
normalized vectors used for inner-product/cosine retrieval.

See [retrieval pipeline](retrieval-pipeline.md) for how those artifacts are used
during search.
