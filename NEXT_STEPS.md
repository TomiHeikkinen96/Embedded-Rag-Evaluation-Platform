# Next Scope: Local LLM Evaluation Harness

This note records the intended next phase of the project so the scope change remains visible between development sessions. It is a design direction, not a claim that every component below is already implemented.

## Immediate Priority: Retrieval Evaluation Matrix

Before adding local model answer generation, the project will first measure the
retrieval foundation across three embedding-model roles, three chunking
strategies, and a literal-search baseline. This makes later answer experiments
easier to interpret because retrieval failures will already be measurable.

See [docs/retrieval-evaluation-plan.md](docs/retrieval-evaluation-plan.md) for the
experiment matrix, ground-truth design, modular architecture, visualization
direction, and staged refactor plan.

## Goal

Build a local-first evaluation harness that measures whether retrieval-augmented context improves local LLM performance on embedded-engineering questions.

The harness should make it possible to answer:

- How well does a model answer without external context?
- Does the current retriever find the information needed to answer?
- Can the model use correctly retrieved information without inventing unsupported details?
- Would the model succeed if it received known-good context?
- Which model, prompt, retrieval, or chunking change caused a measured improvement or regression?

## Core Experiment

Run every benchmark case under comparable conditions:

1. **No context:** the model receives only the question and shared instructions.
2. **Retrieved context:** the model receives context selected by the current retrieval pipeline.
3. **Oracle context:** the model receives a manually verified source excerpt containing the information needed to answer.

The oracle condition is important because it separates retrieval quality from model capability and context utilization.

## Proposed Boundaries

- `retrieval/` exposes a small retriever interface backed initially by the existing FAISS and SQLite search path.
- `models/` owns local model adapters, beginning with an OpenAI-compatible local endpoint such as Ollama.
- `evaluation/` owns benchmark cases, experiment execution, metrics, and result comparison.
- existing `chunkers/`, `processing/`, and `utils/db.py` responsibilities remain explicit.
- framework integrations should be adapters or comparison implementations, not hidden dependencies of the benchmark definition.

Exact paths can be adjusted when implementation begins; preserving the boundaries matters more than adopting this directory layout literally.

## First Milestones

- [ ] Define a structured benchmark-case format with questions, required facts, forbidden claims, reference answers, and stable source locations.
- [ ] Decide how benchmark source labels remain stable across force rebuilds; current random chunk UUIDs should not be permanent ground-truth identifiers.
- [ ] Extract a reusable retriever API from `search_index.py` without changing retrieval behavior.
- [ ] Add a narrow model-client protocol and an Ollama-backed implementation.
- [ ] Save prompts, model settings, retrieved chunks, raw outputs, timing, failures, and scores for every run.
- [ ] Implement the three experimental conditions: no context, retrieved context, and oracle context.
- [ ] Add deterministic retrieval metrics such as Recall@k and MRR.
- [ ] Add answer checks for required facts, unsupported claims, citations, and appropriate refusal.
- [ ] Generate a human-readable comparison report grouped by model and experiment condition.

## Framework Learning Plan

The project can still demonstrate widely used AI application technologies without surrendering its inspectability:

- Keep the first runner as straightforward Python so the experiment is easy to understand.
- Add a LangChain model or tool adapter after the provider boundary is stable.
- Add a small LangGraph runner to compare checkpointed workflow orchestration with the plain runner.
- Add a LlamaIndex retriever or evaluation adapter as a controlled comparison against the custom pipeline.
- Consider Temporal only after long-running or distributed experiment batches create a real recovery requirement.
- Add containers once model service, harness, and storage responsibilities are clear enough to reproduce reliably.

## Guardrails

- Do not describe planned framework integrations as already implemented.
- Do not introduce two frameworks in the same milestone unless the comparison itself is the experiment.
- Keep retrieval metrics separate from generated-answer metrics.
- Prefer human-reviewed reference facts and deterministic checks before relying on LLM-as-judge scores.
- Record enough configuration and artifacts to reproduce every reported result locally.
