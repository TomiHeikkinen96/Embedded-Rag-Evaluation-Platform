# Embedding Explorer

Run:

```bash
./view_evaluation.sh
```

The command embeds the maintained benchmark queries, reconstructs the active
FAISS vectors, generates browser data, waits for the local server, and opens the
interactive page. Pass a port when `8000` is unavailable:

```bash
./view_evaluation.sh 8080
```

## What it shows

- corpus chunk embeddings and benchmark-query embeddings
- a rotatable three-dimensional PCA projection
- original-space cosine similarity for the selected query
- highlighted nearest chunks with source-page and text previews
- simple score-separation diagnostics

The view is useful for exploring broad neighbourhoods, outliers, noisy chunks,
and benchmark coverage.

## What it does not prove

The embedding model produces 384-dimensional vectors in the current baseline.
PCA discards information when projecting them into three dimensions. Apparent
distance in the plot is therefore explanatory, not the distance used by FAISS.

A visually tidy cluster is not retrieval accuracy. Correctness requires labelled
evidence and ranking metrics such as Recall@k and MRR.

## Planned expansion

The explorer will eventually select embedding model, chunking strategy, and
retrieval method. A metrics view below the geometry will compare per-question
reciprocal rank, aggregate recall, latency, and index size. Failures should link
the expected evidence to the retrieved results.
