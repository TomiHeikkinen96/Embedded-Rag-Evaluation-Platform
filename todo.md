# Current State and Next Work

This is the repository's single living status, limitations, and priority list.
Design explanations belong in `docs/`, and completed implementation history
remains available in Git.

## Current demonstrable system

- [x] Incrementally load local PDFs with changed/deleted-file detection and an
  explicit confirmed clean rebuild.
- [x] Create sentence-oriented and first-pass table-aware chunks while retaining
  source document, physical PDF page, heading, and larger paragraph context.
- [x] Build normalized MiniLM, BGE, and Arctic Embed indexes over one shared
  chunk corpus.
- [x] Store inspectable chunk metadata in SQLite and use an explicit
  `(index_id, vector_id) -> chunk_id` mapping for each FAISS index.
- [x] Retrieve a semantic candidate pool, apply chunk-only lexical reranking and
  low-value penalties, deduplicate paragraphs, and return top-k results.
- [x] Ask a local Qwen 3.5 9B model grounded questions through Ollama with
  bounded source labels, citations, refusal instructions, streaming, timing,
  and token metrics.
- [x] Validate retrieval against a hash-locked, human-labelled ESP32 benchmark
  using document, physical page, and text-anchor evidence.
- [x] Compare closed-book, oracle-context, and Arctic dense-RAG generation using
  the same typed questions and deterministic scoring.
- [x] Persist generation manifests, JSONL attempts, summaries, partial-run
  recovery, and historical-input warnings.
- [x] Expose retrieval, distractor, and generation results in one evaluation
  explorer with a frozen offline presentation backup.
- [x] Add unit tests for grounded prompts, source labels, citation parsing,
  answer/refusal scoring, benchmark loading, summaries, and report export.
- [x] Document the fresh-clone question path, assignment-layer mapping,
  evaluation commands, test command, and AI-native development workflow.

## Priority 1 — retrieval quality and prompt cost

This is the most direct continuation of the current experiment.

- [ ] Persist a canonical retrieval run containing resolved configuration,
  ranked results, timing, metrics, and artifact sizes.
- [ ] Add deterministic literal retrieval with meaningful zero-result reporting
  as a transparent comparison to dense retrieval.
- [ ] Compare top-k 3 and top-k 10 generation runs using answer quality,
  evidence hits, latency, and input-token cost—not a hand-picked example.
- [ ] Add an explicit relevance/filtering stage so a weak top-k candidate does
  not automatically consume prompt space merely because FAISS returned it.
- [ ] Evaluate dynamic top-k and context compression, retaining only passages
  that contribute distinct evidence.
- [ ] Compare the current lexical heuristic with a learned cross-encoder
  reranker over the same candidate pool and labelled benchmark.
- [ ] Calibrate refusal separately from ranking: measure whether the system can
  decide that the corpus or retrieved evidence does not support the question.
- [ ] Add claim-level support inspection before claiming that unsupported extra
  statements are automatically detected.

Reranking, filtering, and refusal are separate decisions: reranking orders
candidates, filtering determines whether they deserve prompt budget, and the
answer contract determines whether the supplied evidence supports a response.

## Priority 2 — small full-stack product slice

The next user-facing version would preserve the inspectable pipeline instead of
replacing it with a framework abstraction.

- [ ] Expose ingestion status, grounded questions, cited sources, and usage
  metrics through a small typed REST API, likely FastAPI first.
- [ ] Add a minimal TypeScript/React conversation UI with source expansion and
  visible refusal states.
- [ ] Preserve query and conversation state while allowing retrieval-model or
  experiment selection.
- [ ] Define conversation persistence, deletion, maximum history, summarization,
  and token-budget behaviour before calling chat history "memory."
- [ ] Keep durable agent memory distinct from conversation history and from the
  document corpus; record provenance for anything retained across tasks.
- [ ] Add provider interfaces and test doubles only where the API/UI boundary
  makes replacement or deterministic integration testing useful.

## Priority 3 — bounded agentic evidence loop

Dense RAG currently retrieves first and always supplies the results. The first
agentic comparison should remain smaller and more measurable than a general
autonomous agent.

- [ ] Add a bounded literal-search tool over normalized extracted corpus text.
- [ ] Let the model choose whether to search, inspect returned evidence, refine
  once within strict limits, and then answer or refuse.
- [ ] Validate tool names and arguments, cap calls and returned characters, and
  never execute model-authored shell commands.
- [ ] Persist the complete observation trace, tool-call count, failures, and
  recovery decisions.
- [ ] Compare the tool loop with closed-book, oracle, and fixed dense RAG using
  the same questions, answer contract, model, and limits.
- [ ] Consider LangGraph or another orchestration framework only as a comparison
  after the plain Python loop is measured and understandable.

## Priority 4 — production design questions

These are important interview and architecture topics, but implementing all of
them would exceed the intentionally small prototype.

- [ ] Define authentication, authorization, tenant identity, and document/index
  isolation for a multi-tenant service.
- [ ] Design asynchronous, idempotent ingestion jobs with retries, progress,
  cancellation, versioning, and safe reindexing.
- [ ] Move local artifacts to durable managed storage with backup, migration,
  retention, and deletion policies.
- [ ] Add secrets management, PII/sensitive-data classification and redaction,
  document-level access controls, and prompt-injection handling.
- [ ] Add structured logging, traces across retrieval and generation, quality
  metrics, cost budgets, rate limits, timeouts, and provider failure handling.
- [ ] Run deterministic evaluation and regression thresholds in CI/CD against a
  safe versioned corpus.
- [ ] Define deployment, scaling, index refresh, cache, and rollback strategies.
- [ ] Add API versioning and integration contracts suitable for a long-lived
  system containing both modern and legacy clients.

## Priority 5 — wider controlled experiments

- [ ] Add a clean-built `raw500` evaluation condition: sequential windows of
  at most 500 characters, no overlap, no physical-page crossing, and retained
  source/page evidence metadata.
- [ ] Add a standalone recursive-character chunker after the raw-500 baseline.
- [ ] Define typed chunker and retriever registries around the existing embedding
  registry and multi-index schema.
- [ ] Compare the complete chunker, embedding, and retrieval matrix while
  changing one declared variable at a time.
- [ ] Separate generated-artifact lifecycles without duplicating pipeline code:
  evaluation builds should rechunk a locked corpus into disposable,
  reproducible condition artifacts, while the generic ingestion demonstration
  should retain SHA-256 changed/deleted-file tracking for one active pipeline.
- [ ] Give evaluation and incremental ingestion distinct storage namespaces and
  task-oriented commands so an experiment cannot silently mutate the active
  incremental index.
- [ ] Redesign cleanup semantics after the evaluation/ingestion split:
  condition-specific `--clean` should require explicit selectors such as
  `--model` and fail safely when they are absent; reserve `--force-clean` for a
  confirmed global deletion and enumerate affected artifacts before removal.
- [ ] Fit PCA on corpus vectors and transform queries through fixed axes; keep
  PCA explanatory rather than treating it as retrieval correctness.
- [ ] Add latency, chunk count, size distribution, and index-size reports.
- [ ] Benchmark native MPS ingestion against Docker/Colima CPU for time, memory,
  and output equivalence before claiming the extra workflow is worthwhile.
- [ ] Consider a hosted embedding or generation baseline only after recording
  API cost, privacy, rate-limit, and snapshot-reproducibility trade-offs.
- [ ] Define at least one hardware-observable embedded task with compilation,
  test, device-output, or measurement evidence.

## Known limitations

- PDFs are local and ignored by Git; a fresh clone must supply documents before
  ingestion, and the committed benchmark requires its exact locked editions.
- PDF tables remain the noisiest source format.
- The current reranker is semantic similarity plus exact-token overlap and a
  hand-written penalty, not a learned query-document relevance model.
- Every selected top-k result enters the prompt after per-source character
  truncation; there is no relevance gate or context compressor yet.
- Weak semantic matches can therefore survive in lower ranks and consume tokens.
- Ambiguous and corpus-negative retrieval controls are recorded but not yet
  included in aggregate retrieval scoring.
- Multi-evidence questions use first-relevant-evidence ranking; evidence-set
  completeness is not a separate metric.
- Generation fact scoring uses normalized accepted substrings. It does not
  understand negation or prove that additional free-form claims are supported.
- Refusal is instructed and evaluated, but the interactive pipeline still
  relies on the model to judge whether retrieved excerpts establish an answer.
- Unit tests currently emphasize generation contracts and reporting; chunking,
  ingestion, retrieval ranking, vector mapping, and mocked end-to-end behaviour
  need broader automated coverage.
- The current CLI is local and single-user. There is no API, conversation UI,
  authentication, tenant isolation, or durable conversation memory.
- Current `--clean`/`--force-rebuild` behaviour is global: it deletes generated
  metadata and every FAISS index, then rebuilds only the selected models. Model-
  specific cleanup and the proposed `--force-clean` distinction are plans, not
  implemented command semantics.

## Evidence retained from completed experiments

- **2026-08-12 — labelled retrieval:** expanded retrieval v1 to 28 cases: 25
  active positives, one ambiguous control, and two corpus-negative controls.
  Labels cover exact identifiers, paraphrases, multi-fact questions, tables,
  conceptual explanations, and errata diagnosis.
- **2026-08-12 — distractors:** added three non-ESP32 datasheets. The recorded
  corpus contained 30,959 chunks: 14,353 ESP32 target chunks and 16,606
  deliberate distractor chunks.
- **2026-08-12 — Apple Silicon:** MiniLM and BGE completed on MPS, but Jina's
  remote custom model code crashed during native MPS initialization after
  working on CPU. Arctic Embed replaced it with a standard, repeatable loading
  path.
- **2026-08-17 — first canonical generation run:** 21 attempts recorded 14.3%
  closed-book, 71.4% oracle, and 71.4% Arctic-RAG contract pass rates. Manual
  review showed that two oracle failures were scorer-label gaps, while one dense
  RAG answer was genuinely wrong despite retrieving a gold page.
- **2026-08-17 — prompt cost:** Arctic retrieval averaged 0.40 seconds, while
  most of the latency difference from oracle came from evaluating a much larger
  prompt: 1,660 versus 172 average prompt tokens.
- **2026-08-17 — evaluation discipline:** historical run artifacts were kept
  immutable when questions and accepted variants were tightened; unsupported
  extra claims remain an explicit manual-review signal.
