# Embedding Explorer

Run:

```bash
./view_evaluation.sh
```

The command embeds the maintained benchmark queries with each registered model,
reconstructs all three FAISS indexes, generates browser data, waits for the
local server, and opens the interactive page. Pass a port when `8000` is
unavailable:

```bash
./view_evaluation.sh 8080
```

## What it shows

- corpus chunk embeddings and benchmark-query embeddings
- large MiniLM, BGE, and Arctic Embed model selectors
- one question selection that persists while switching models
- a rotatable three-dimensional PCA projection
- original-space cosine similarity for the selected query
- highlighted nearest chunks with source-page and text previews
- dimensions, three-component explained variance, and score separation

The view is useful for exploring broad neighbourhoods, outliers, noisy chunks,
and benchmark coverage.

## What it does not prove

The models produce either 384- or 768-dimensional vectors. PCA is fitted on
each model's corpus and discards information when projecting it into three
dimensions. Apparent distance and orientation across two model plots are
therefore explanatory, not directly comparable and not the distance used by
FAISS.

A visually tidy cluster is not retrieval accuracy. Correctness requires labelled
evidence and ranking metrics such as Recall@k and MRR.

## Planned expansion

Embedding-model selection is implemented. The explorer will eventually add
chunking-strategy and retrieval-method controls. A metrics view below the
geometry will compare per-question
reciprocal rank, aggregate recall, latency, and index size. Failures should link
the expected evidence to the retrieved results.
