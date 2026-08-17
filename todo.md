# Todo

This is the concise working list for the current development phase. Design
detail belongs in `docs/`; completed history remains available in Git.

## Current milestone — labelled retrieval baseline

- [x] Define `benchmarks/esp32-retrieval-v1` with a hash-locked corpus manifest,
  stable case ids, questions, answerability labels, and source evidence.
- [x] Label an initial varied set of 20–30 cases, including exact identifiers,
  paraphrases, table values, broad questions, ambiguous questions, and absent answers.
- [x] Add benchmark validation that fails when a corpus hash, document page, or
  text anchor no longer resolves.
- [x] Calculate reciprocal rank, MRR, and Recall@1/3/5/10 for available current
  custom-chunker embedding indexes and expose per-case ranked evidence.
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
- [ ] Add latency, chunk count, and index-size views. Per-question reciprocal
  rank and aggregate MRR/Recall@k are implemented in the golden comparison.
- [ ] Add expected-evidence versus retrieved-result failure inspection.
- [x] Add wrong-device distractor reporting: first intrusion rank, top-k counts,
  target precision, gold-score margin, and per-device confusion.
- [x] Add top-level Retrieval and Generation evaluation navigation, saved-run
  selection, partial-run recovery, timing comparison, and per-case generation
  inspection to `view_evaluation.sh`.

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

- [x] Select Qwen 3.5 9B and add a reproducible local Ollama Modelfile.
- [x] Add `ask_question.sh` with Arctic retrieval, bounded source-labelled
  context, local Qwen generation, citations, streaming, and usage metrics.
- [x] Add closed-book, Arctic dense-RAG, and oracle-context generation runs
  using the same model and questions. Bounded grep remains the next condition.
- [x] Add typed exact-value, identifier, multi-fact, and unanswerable generation
  cases with deterministic answer normalization.
- [x] Add initial deterministic fact, refusal, citation, and evidence-page
  checks before LLM judging. Compilation checks belong to later code tasks.
- [ ] Define at least one hardware-observable embedded benchmark task.
- [ ] Add broader agentic planning and tools only after the bounded grep and
  supplied-context generation conditions are measurable.

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
- `benchmark_queries.txt` remains an unlabelled legacy query list; labelled
  ground truth lives in `benchmarks/esp32-retrieval-v1`.
- Ambiguous and unanswerable controls are recorded but not yet scored.
- Multi-evidence questions currently receive first-relevant-evidence ranking;
  evidence-set completeness is not yet a separate metric.
- Weak semantic matches can survive in lower ranks.
- PCA is explanatory and cannot establish retrieval correctness.
- Qwen's first negative-case run clearly refused but added an explanation after
  the requested exact refusal sentence. The generation answer contract and
  scorer must distinguish refusal intent from exact-format compliance.
- Generation fact scoring uses normalized accepted substrings. It does not yet
  understand negation or automatically detect unsupported additional claims;
  raw answers and supplied sources remain in JSONL for inspection.

## Evaluation log

- 2026-08-12: Inventoried the three PDFs under `data/`. Although they were
  reached from the ESP-IDF v4.3 Hardware Reference page, the rolling downloads
  are Datasheet v5.3, TRM v5.8, and SoC Errata v3.0—not a v4.3 snapshot.
- 2026-08-12: Converted the eight legacy search fragments into seven active
  human-verifiable cases and one `needs_review` case. `maximum current` is not
  scoreable without specifying the current domain and operating condition.
- 2026-08-12: Added a modular top-level evaluation view switcher and golden
  comparison. Strict hits require document, physical PDF page, and text anchor;
  correct-page/wrong-passage results remain visible as near misses.
- 2026-08-12: Expanded retrieval v1 to 28 cases: 25 active positives across all
  three PDFs, one ambiguous control, and two corpus-negative controls. New
  labels cover exact identifiers, paraphrases, multi-fact questions, tables,
  conceptual explanations, and hardware errata diagnosis.
- 2026-08-12: Added PIC24FJ, STM32F446, and ATmega328P datasheets as deliberate
  wrong-device distractors. The corpus now has 30,959 chunks: 14,353 ESP32
  target chunks and 16,606 distractor chunks. ESP32 golden labels remain the
  correct scope; separate labels would be needed only for a multi-device task.
- 2026-08-12: Replaced the eight terse legacy PCA queries with six representative
  benchmark-style questions and added a third GUI view for distractor intrusion.
  Counts report corpus noise directly; exact evidence correctness remains in the
  separate golden comparison.
- 2026-08-12: Native MPS ingestion completed MiniLM and BGE over 14,353 chunks,
  then Jina's remote custom model code caused a process-level segmentation fault
  during model initialization. Replaced it with standard-BERT Arctic Embed M
  v1.5 so the three-model baseline remains repeatable on Apple Silicon.
- 2026-08-15: Selected Qwen 3.5 9B as the cheap local generation baseline and
  defined four evidence-access conditions: closed-book, bounded grep agent,
  dense RAG, and oracle context. Retrieval and tool access remain harness
  concerns so every condition can use the same model definition.
- 2026-08-17: Completed the first Arctic-to-Qwen grounded-answer path. A labelled
  positive query returned the correct 3.3 V, 1.8 V, and 40 mA values with the
  expected TRM page citation. The native-USB negative query refused but did not
  obey the exact-output constraint, motivating explicit refusal-format scoring.
- 2026-08-17: Added the first generation evaluation runner with seven committed
  cases and closed-book, oracle, and Arctic dense-RAG conditions. Runs persist
  their resolved manifest, each attempt as JSONL, and aggregate summary. The
  deterministic scorer keeps refusal intent separate from exact refusal format
  and records evidence-page retrieval hits separately from answer correctness.
- 2026-08-17: The first 21-attempt canonical generation run recorded 14.3%
  closed-book, 71.4% oracle, and 71.4% Arctic-RAG pass rates. Manual review found
  both oracle failures were accepted-phrase gaps, not model errors; the GPIO
  Arctic answer was genuinely wrong despite a gold-page hit, and the deep-sleep
  question was underspecified relative to the multiple power modes in the
  datasheet. Accepted variants and the deep-sleep question were tightened for
  future runs without rewriting the historical artifact.
- 2026-08-17: In that run, average pipeline time was 23.38 s closed-book, 5.26 s
  oracle, and 20.17 s Arctic RAG. Arctic context retrieval averaged 0.40 s; most
  of its 14.91 s gap to oracle came from evaluating a much larger prompt (1660
  versus 172 average prompt tokens), not FAISS retrieval. Closed-book generated
  much longer answers and was 3.21 s slower than Arctic RAG on average.
- 2026-08-17: Generation reporting now exposes average and whole-run input,
  output, and total token counts per condition. Existing artifacts remain
  compatible because missing total counts are derived from input plus output.
- 2026-08-17: Rechecked two generation failures against the local PDFs. The
  classic ESP32 Datasheet and TRM contain no native USB D+/D-/OTG assignment,
  so the closed-book GPIO 15/GPIO 4 answer is unsupported. The Datasheet states
  10 µA in its Features section, while 100 µA refers specifically to the ULP
  sensor-monitored pattern; the Arctic failure retrieved the wrong operating
  condition. No historical benchmark artifacts were rewritten.
- 2026-08-17: Split generation reporting into overall contract pass,
  required-fact presence, corpus-negative refusal, and unsupported-extra-claim
  review. Extra claims remain explicitly manual because normalized substring
  matching cannot establish contradiction or full-answer correctness.
