# Evaluation Explorer

Run:

```bash
./view_evaluation.sh
```

The command embeds the maintained benchmark queries with each registered model,
reconstructs all three FAISS indexes, exports saved generation runs, waits for
the local server, and opens the interactive page. Pass a port when `8000` is
unavailable:

```bash
./view_evaluation.sh 8080
```

The viewer owns one labelled container named `rageval-evaluation-server`.
Starting it again replaces only that exact managed server, and `Ctrl+C`
explicitly removes the container instead of merely stopping the local Compose
client. If another application owns the requested port, the script exits before
regenerating visualization data and suggests selecting another port.

## What it shows

The top-level **Evaluation** switch separates **Retrieval** from **Generation**.
Retrieval contains the existing embedding, golden-evidence, and distractor
views. Generation contains:

- completed and partial run selection, preferring the latest completed
  canonical run
- overall grounded-contract pass, required-fact presence, corpus-negative
  refusal, citation, and gold-evidence-hit rates by condition
- an explicit manual-review signal for unsupported or contradictory additional
  claims, which deterministic phrase checks do not establish
- context, generation, total pipeline, and throughput comparisons
- average and whole-run input, output, and total token usage by condition
- pipeline-time delta and ratio against oracle context
- per-question answers, deterministic fact checks, citations, supplied
  excerpts, and timing

For runs containing dense RAG, the run selector and selected-run status show
the saved retrieval depth so top-k comparison runs remain distinguishable.

Required-fact coverage counts accepted facts found in answers; it does not mean
the complete answer is correct. Overall contract pass additionally applies the
condition's refusal and citation rules. Unsupported or contradictory extra
claims remain visible in the raw answer and are deliberately labelled for
manual review rather than assigned a misleading automatic score.

Generation visualization data is derived from `runs/generation/`. A finalized
run uses its saved summary. If evaluation stopped before writing `summary.json`,
the exporter derives a partial summary from the completed JSONL lines. Opening
the viewer never requires rerunning the generation benchmark; it snapshots the
available artifacts when `view_evaluation.sh` starts.
If a run's recorded input hashes differ from the current benchmark or
Modelfile, the page marks it as historical rather than silently rescoring it.

Retrieval views show:

- corpus chunk embeddings and benchmark-query embeddings
- large MiniLM, BGE, and Arctic Embed model selectors
- one question selection that persists while switching models
- a rotatable three-dimensional PCA projection
- original-space cosine similarity for the selected query
- highlighted nearest chunks with source-page and text previews
- dimensions, three-component explained variance, and score separation
- golden-evidence MRR and Recall@1/3/5/10 with per-question failure inspection
- a distractor-intrusion report comparing wrong-device ranks and counts,
  target-corpus precision, gold-to-distractor score margins, and per-device confusion

The view is useful for exploring broad neighbourhoods, outliers, noisy chunks,
and benchmark coverage.

The 3D explorer intentionally uses six representative questions: table lookup,
pin lookup, conceptual explanation, memory-role paraphrase, errata diagnosis,
and an unanswerable control. The complete labelled set remains in the golden
comparison instead of becoming a crowded row of query buttons.

## Distractor report definitions

- **Mean first wrong rank** averages the rank of the first distractor for cases
  where one appears in the top 10. The adjacent per-device table makes the
  omitted no-intrusion cases visible through its counts.
- **Wrong chunks @k** is the total number of distractor-role results across all
  active benchmark questions, not a percentage.
- **Target precision @k** is the share of returned result slots belonging to
  any target-role ESP32 document. This measures source-family discrimination;
  the golden view separately checks the exact document, page, and passage.
- **Mean gold margin** is the first gold result's rerank score minus the
  highest-ranked distractor score, averaged only over cases where both occur in
  the top 10. Positive is desirable. The comparable-case count is shown beside it.

## What it does not prove

The models produce either 384- or 768-dimensional vectors. PCA is fitted on
each model's corpus and discards information when projecting it into three
dimensions. Apparent distance and orientation across two model plots are
therefore explanatory, not directly comparable and not the distance used by
FAISS.

A visually tidy cluster is not retrieval accuracy. Correctness requires labelled
evidence and ranking metrics such as Recall@k and MRR.

## Planned expansion

Embedding-model selection and the first generation-run dashboard are
implemented. The explorer will eventually add
chunking-strategy and retrieval-method controls. A metrics view below the
geometry will compare per-question
reciprocal rank, aggregate recall, latency, and index size. Failures should link
the expected evidence to the retrieved results.
