# Next Checkpoint

The project is in **Phase 1: context and retrieval evaluation**.

## Immediate objective

Turn the current repeatable query list into a small human-labelled ESP32
retrieval benchmark before adding more embedding models or changing storage.

## Implementation order

1. Define a versioned benchmark case format.
2. Label stable evidence by document, page, and text anchor.
3. Validate that every evidence label resolves against the current corpus.
4. Capture current custom-chunker/MiniLM results as the regression baseline.
5. Extract typed chunker, embedding, index, and retriever configurations.
6. Refactor storage so several chunk sets and FAISS indexes can coexist.
7. Add raw-500 and LangChain recursive chunking baselines.
8. Add the medium and technical embedding candidates.
9. Add literal retrieval, MRR, Recall@k, latency, and artifact-size reporting.
10. Make the browser explorer consume saved evaluation runs.

## Guardrails

- One configurable pipeline; no duplicated implementation per model/chunker.
- Change one declared experimental variable at a time.
- Keep retrieval scoring separate from generated-answer scoring.
- Treat cosine and PCA as diagnostics, not correctness metrics.
- Preserve incremental local workflows and explicit clean rebuilds.
- Do not present planned stages as implemented.

See the [evaluation overview](docs/evaluation.md),
[detailed retrieval plan](docs/retrieval-evaluation-plan.md), and
[roadmap](docs/roadmap.md).
