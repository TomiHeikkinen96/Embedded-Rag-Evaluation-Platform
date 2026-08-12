# Roadmap

The roadmap deliberately builds measurement before autonomy. Later phases may
change as experiments reveal what is useful.

## Phase 1 — Context and retrieval evaluation

Status: current.

Implemented foundation:

- incremental PDF ingestion and deletion handling
- custom prose/table-aware chunking
- normalized MiniLM embeddings and FAISS indexing
- explicit SQLite vector-to-chunk metadata
- retrieval, heuristic reranking, batch queries, and inspection tools
- interactive 3D embedding explorer

Completion target:

- human-labelled ESP32 retrieval benchmark
- three chunking strategies and three embedding models
- literal baseline plus dense retrieval
- reproducible run artifacts with MRR, Recall@k, latency, and storage costs
- explorer controls and failure inspection

## Phase 2 — Grounded generation evaluation

Status: planned.

- compare no-context, retrieved-context, and oracle-context conditions
- compare a practical local coding model with selected hosted APIs
- record prompts, model versions, settings, context, output, latency, and failures
- score required facts, unsupported claims, citations, and refusal behaviour

Completion means retrieval failure, model capability, and context-use failure can
be distinguished in a saved experiment.

## Phase 3 — Hardware-verified engineering tasks

Status: planned.

- define small embedded coding tasks with deterministic build/test criteria
- compile generated code and run available automated tests
- add simulator or hardware-in-the-loop checks where they provide real evidence
- capture observations such as serial logs, timing, logic traces, or measurements
- retain human review for physical behaviour that cannot be reduced safely to one metric

Completion means at least one end-to-end task is judged by observable engineering
behaviour rather than text similarity alone.

## Phase 4 — Agentic engineering harness

Status: exploratory.

- expose retrieval, build, test, and observation as explicit tools
- add planning and bounded iteration
- persist traces and failure states
- test recovery after failed builds or incorrect assumptions
- compare a transparent custom loop with selected framework implementations

Completion means the system can attempt, observe, and revise an embedded task
while every consequential step remains inspectable.

## Non-goals

- claiming a generally superior coding agent from one corpus
- treating a framework integration as evaluation
- using an LLM judge as the only source of truth
- hiding failed or zero-result benchmark cases
- adding orchestration before the underlying experiment needs it
