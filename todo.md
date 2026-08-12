# Todo

This is the concise working list for the current development phase. Design
detail belongs in `docs/`; completed history remains available in Git.

## Current milestone — labelled retrieval baseline

- [ ] Define `benchmarks/esp32-retrieval-v1` with stable case ids, questions,
  topics, and source-evidence labels.
- [ ] Label an initial varied set of 20–30 cases, including exact identifiers,
  paraphrases, table values, broad questions, ambiguous questions, and absent answers.
- [ ] Add benchmark validation that fails when a document/page/text anchor no
  longer resolves.
- [ ] Calculate reciprocal rank, MRR, and Recall@1/3/5/10 for the current
  custom-chunker/MiniLM baseline.
- [ ] Persist the baseline configuration, ranked results, timing, and metrics.

## Next — configurable retrieval matrix

- [ ] Define typed registries for chunkers and retrievers. The embedding-model
  registry is implemented.
- [x] Separate shared chunk identity from embedding/index identity in SQLite.
- [x] Support several FAISS indexes without overwriting one active state.
- [ ] Add raw 500-character chunking.
- [ ] Add LangChain's standalone recursive-character splitter.
- [x] Add BGE and Arctic medium retrieval candidates; replace Jina after its
  custom model code crashed under native macOS MPS initialization.
- [ ] Add transparent literal retrieval and zero-result reporting.
- [ ] Compare the complete matrix using the same labelled benchmark and top-k budget.

## Explorer and reporting

- [ ] Fit PCA on corpus vectors and transform queries through fixed axes.
- [x] Report explained variance for the displayed components.
- [ ] Add chunker and retrieval-method controls. Model selection is implemented.
- [ ] Add per-question reciprocal rank, aggregate MRR/Recall@k, latency, chunk
  count, and index-size views.
- [ ] Add expected-evidence versus retrieved-result failure inspection.

## Environment and performance

- [ ] Test whether native macOS PyTorch MPS accelerates ingestion compared with
  the Docker/Colima CPU path. Verify all three models, output equivalence,
  memory use, and whether the extra host workflow is worth maintaining.
- [x] Add an optional native macOS ingestion wrapper with an isolated Python
  3.12 environment and explicit MPS availability check.
- [ ] Consider `text-embedding-3-large` as an optional hosted retrieval
  baseline after the local labelled baseline is recorded. Keep API cost,
  privacy, rate limits, and weaker snapshot reproducibility explicit.

## Later phases

- [ ] Add no-context, retrieved-context, and oracle-context generation runs.
- [ ] Add deterministic answer and compilation checks before LLM judging.
- [ ] Define at least one hardware-observable embedded benchmark task.
- [ ] Add agentic planning/tools only after retrieval and generation are measurable.

## Completed foundation

- [x] Incremental PDF ingestion with hashing, changed/deleted-file handling, and
  explicit clean rebuild confirmation.
- [x] Sentence-oriented and first-pass table-aware chunking with low-value filtering.
- [x] Normalized MiniLM embeddings, FAISS indexing, and explicit SQLite vector mapping.
- [x] Chunk-only lexical reranking, low-value penalties, and paragraph deduplication.
- [x] Search, batch-query, database-inspection, and index-integrity tools.
- [x] Docker/Colima workflow with task-oriented root scripts.
- [x] Interactive 3D PCA explorer using original-space cosine scores.
- [x] Three-model explorer with persistent question selection across model switches.
- [x] Per-model load, embedding-throughput, index-write, and total timing output.
- [x] Retrieval-evaluation matrix and staged architecture plan.

## Current known limitations

- PDF tables remain the noisiest source format.
- The current query file is repeatable but not yet labelled ground truth.
- The model indexes are comparable, but retrieval accuracy is not yet labelled or scored.
- Weak semantic matches can survive in lower ranks.
- PCA is explanatory and cannot establish retrieval correctness.
