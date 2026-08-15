# Next Checkpoint

The project is moving from the implemented labelled retrieval baseline into a
thin **Phase 2: grounded generation** slice. The remaining retrieval matrix can
continue afterward without blocking the first answer-quality experiment.

## Immediate objective

Run Qwen 3.5 9B against a small, deterministically scored question set while
changing only how the model can obtain evidence.

## Implementation order

1. Install native Ollama and create `rageval-qwen` from the checked-in Modelfile.
2. Define typed boolean, exact-value, identifier, and unanswerable cases by
   extending or mapping the existing labelled benchmark.
3. Add a narrow Ollama provider and record the resolved model, prompt, settings,
   response, latency, and failure for every run.
4. Implement closed-book and oracle-context runs first.
5. Add supplied dense-RAG context using the existing retrieval pipeline.
6. Add one bounded literal-search tool over normalized extracted corpus text.
7. Score normalized answers, abstention, evidence correctness, unsupported
   claims, latency, and tool-call count across all four conditions.
8. Save a comparable run artifact before adding broader planning or frameworks.

## Guardrails

- One configurable pipeline; no duplicated implementation per model/chunker.
- Change one declared experimental variable at a time.
- Keep retrieval scoring separate from generated-answer scoring.
- Use the same model definition, questions, answer contract, and limits across
  closed-book, grep-agent, dense-RAG, and oracle-context runs.
- Keep evidence access in the harness; do not bake RAG or tools into the Modelfile.
- Treat cosine and PCA as diagnostics, not correctness metrics.
- Preserve incremental local workflows and explicit clean rebuilds.
- Do not present planned stages as implemented.

See the [local model workflow](docs/local-model.md),
[evaluation overview](docs/evaluation.md),
[detailed retrieval plan](docs/retrieval-evaluation-plan.md), and
[roadmap](docs/roadmap.md).
