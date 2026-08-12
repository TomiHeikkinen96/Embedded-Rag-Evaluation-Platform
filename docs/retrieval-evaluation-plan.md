# Retrieval Evaluation Plan

Status: proposed Phase 1 work; only the current custom-chunker/MiniLM path is
implemented.

## Question

Which embedding model, chunking strategy, and retrieval method finds manually
verified ESP32 evidence most reliably—and what does each option cost in time,
storage, and complexity?

This phase comes before generation because an answer experiment is difficult to
interpret while retrieval quality is unknown.

## Hypotheses

The experiment will test these assumptions rather than build around them:

- Domain-aware sentence/table chunking outperforms raw fixed-width chunks.
- A generic recursive splitter is a strong conventional baseline but may lose
  datasheet table context.
- A medium retrieval model improves ranking enough to justify its cost over the
  small baseline.
- A technical/code-biased model handles identifiers and engineering language
  better, but may be weaker on ordinary prose.
- Literal search is competitive for exact identifiers but cannot bridge many
  paraphrases.
- Dense and literal retrieval may eventually work best as a hybrid.

Negative findings are valid results. In particular, the custom chunker and the
technical model are not assumed winners.

## Experiment matrix

### Embedding models

| Alias | Candidate | Experimental role |
| --- | --- | --- |
| `mini` | `sentence-transformers/all-MiniLM-L6-v2` | Fast 384-dimensional general baseline and current behaviour |
| `bge` | `BAAI/bge-base-en-v1.5` | Medium 768-dimensional retrieval model |
| `technical` | `jinaai/jina-embeddings-v2-base-code` | Technical/code-biased candidate requiring a compatibility spike |

Store the complete model id, pinned revision, dimensionality, normalization,
maximum input length, and query/document prefix policy. The technical candidate
uses remote model code, so review and pin it before adoption.

Before accepting any new model on the CPU-only Apple Silicon environment,
measure model loading, memory, embedding throughput, query latency, and artifact
size.

Primary model references:

- [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [BGE base v1.5 model card](https://huggingface.co/BAAI/bge-base-en-v1.5)
- [Jina code embeddings model card](https://huggingface.co/jinaai/jina-embeddings-v2-base-code)

### Chunking strategies

| Alias | Strategy | Experimental role |
| --- | --- | --- |
| `custom` | Current sentence/table-aware PDF chunker | Domain-aware implementation under test |
| `recursive` | LangChain `RecursiveCharacterTextSplitter`, initially 500 characters and 100 overlap | Conventional generic RAG baseline |
| `raw500` | Sequential 500-character windows without overlap or boundary awareness | Deliberately naive control |

Use only the standalone LangChain splitter. Feed all three outputs through the
same SQLite, embedding, FAISS, retrieval, and evaluation code. A complete
LangChain or LlamaIndex pipeline would change several variables at once and can
be compared later as a separate end-to-end system.

Report chunk count, character/token size distribution, overlap, and index size.
If chunk size dominates the result, add a second size-controlled experiment
instead of silently tuning one strategy until it wins.

### Retrieval methods

| Alias | Behaviour |
| --- | --- |
| `dense` | Original-space cosine similarity from the selected embedding index |
| `literal` | Deterministic exact phrase and token matching over a selected chunk set |
| `hybrid` | Later rank combination after both baselines are understood |

The first literal baseline should rank normalized exact phrases first, then all
meaningful query tokens, then decreasing token coverage. If no meaningful token
matches, it returns no result. Its zero-result rate is useful evidence.

BM25 is a possible later lexical method, not another name for this literal
control.

The initial matrix contains:

- 9 dense conditions: 3 models × 3 chunkers
- 3 literal conditions: literal search × 3 chunkers
- no hybrid conditions until the two baselines are understood

## Fair-comparison rules

- Use the same corpus revision and benchmark version.
- Use the same top-k evaluation window.
- Keep source loading and relevance matching constant.
- Record every model, chunker, and retriever parameter.
- Retain failed and zero-result cases.
- Do not tune against the final reported cases without recording the iteration.
- Change one declared variable at a time where possible.

Raw cosine values are not comparable accuracy scores across model families. A
model producing `0.75` is not necessarily better than one producing `0.45`.
Compare labelled ranks; use cosine distributions and PCA to investigate them.

## Benchmark and ground truth

`benchmark_queries.txt` is currently a repeatable query list, not ground truth.
The first implementation milestone is a versioned benchmark such as
`benchmarks/esp32-retrieval-v1.yaml`.

Example shape:

```yaml
id: pull-up-resistor-value
question: What is the resistance of the internal pull-up resistor?
topic: electrical-characteristics
relevant_evidence:
  - document: esp32-wroom-32u_datasheet_en.pdf
    page: 26
    text_anchor: Resistance of internal pull-up resistor
```

Labels identify stable evidence, not random chunk ids. Chunk boundaries vary by
strategy; the underlying source evidence does not. Benchmark validation should
fail for human review if a document, page, or text anchor no longer resolves.

The initial 20–30 cases should include:

- exact identifiers and quoted terminology
- paraphrases without literal word overlap
- table-value questions
- broad conceptual questions
- ambiguous questions
- questions not answered by the corpus

## Metrics

The initial per-question `0..1` comparison value is reciprocal rank:

```text
RR = 1 / rank of the first relevant result
```

- rank 1 → `1.0`
- rank 2 → `0.5`
- rank 3 → `0.333`
- absent from the evaluation window → `0.0`

Report:

- reciprocal rank and mean reciprocal rank
- Recall@1, Recall@3, Recall@5, and Recall@10
- literal-query coverage and zero-result rate
- ingestion time and query latency
- chunk count, size distribution, and FAISS size
- top cosine and score separation only as diagnostics

Add nDCG only if relevance becomes graded. Human labels are preferable to an LLM
judge while this benchmark remains small.

See [evaluation](evaluation.md) for how retrieval metrics later connect to
generation and hardware validation.

## Persisted identity

The current schema assumes one active embedding model and stores model identity
on chunks. The comparison needs separate identities:

- document: source path plus content hash
- chunking configuration: strategy, parameters, and version
- chunk: document, chunking configuration, source span, and text hash
- embedding configuration: model revision and encoding policy
- index: corpus, chunk-set, and embedding identities
- evaluation run: benchmark, retriever/index configuration, and code revision

`indexed_chunks` should eventually identify `(index_id, vector_id)` because
different FAISS indexes may reuse vector ids safely.

Example artifact paths:

```text
storage/indexes/custom/mini.faiss
storage/indexes/custom/bge.faiss
storage/indexes/raw500/technical.faiss
```

SQLite remains the inspectable metadata layer. Using a LangChain splitter does
not require adopting its vector-store abstraction.

## Command direction

Keep selectors strict and task-oriented:

```bash
./ingest_data.sh --model mini --chunker custom
./ingest_data.sh --model all --chunker all
./run_evaluation.sh --all
./view_evaluation.sh
```

These selectors and `run_evaluation.sh` are planned, not currently available.
Ordinary ingestion should keep a fast targeted default; building all nine dense
indexes must remain explicit on the M1.

Python entry points remain usable through `run_script.sh`, and root shell scripts
remain Docker conveniences rather than the core business logic.

## Implementation sequence

1. Define, label, and validate benchmark cases.
2. Capture the current custom/MiniLM result as a regression baseline.
3. Define typed chunker, embedder, retriever, and experiment configurations.
4. Separate chunk-set and embedding/index identities in storage.
5. Add raw-500 and recursive chunkers with source-evidence validation.
6. Add medium and technical model candidates after compatibility checks.
7. Add literal retrieval and persist all ranked results and metrics.
8. Refactor the explorer to consume saved runs and expose experiment controls.
9. Consider hybrid retrieval only after inspecting baseline failures.
10. Carry the best-understood configurations into grounded generation evaluation.

## Convincing outcome

The experiment succeeds when its evidence is human-verifiable, its configuration
is reproducible, ranking metrics support its claims, costs remain visible, and
the visualization explains failures without being presented as proof.
