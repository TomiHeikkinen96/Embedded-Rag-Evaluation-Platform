# Retrieval Evaluation And Exploration Plan

Status: proposed immediate direction, not yet implemented.

This plan turns the current single-model RAG demo into an inspectable retrieval
experiment. The immediate question is no longer only “does search return
something?” It is:

> Which embedding model, chunking strategy, and retrieval method finds the
> manually verified ESP32 evidence most reliably, and what does each trade for
> speed, storage, and inspectability?

The later local-LLM experiment remains valuable. This retrieval phase should
come first because answer evaluation is difficult to interpret when retrieval
quality is still unknown.

## Experimental Questions

The first experiment should test the following hypotheses without assuming they
are true:

1. The custom sentence/table-aware chunker retrieves technical evidence more
   reliably than fixed 500-character chunks.
2. LangChain's generic recursive splitter is a strong conventional baseline,
   but domain-aware table handling may outperform it on datasheets.
3. A larger general retrieval model improves ranking over the fast MiniLM
   baseline enough to justify its extra time and storage.
4. A code/technical-biased model handles identifiers and engineering language
   better than general models. It may also perform worse on ordinary prose; that
   is a useful result rather than a failed demo.
5. Literal search is competitive for exact identifiers and quoted terminology,
   but dense retrieval is more useful for paraphrases and underspecified
   questions.
6. A later hybrid retriever may outperform either dense or literal retrieval
   alone.

These hypotheses should be recorded before looking at the final benchmark
results so the project does not become a collection of favourable examples.

## Comparison Matrix

### Embedding models

Use stable short aliases in commands and store the full model identifier,
revision, dimensionality, normalization, maximum input length, and query-prefix
policy in experiment metadata.

| Alias | Proposed model | Role | Important constraint |
| --- | --- | --- | --- |
| `mini` | `sentence-transformers/all-MiniLM-L6-v2` | Fast, small general baseline; also preserves the current result | 384 dimensions and inputs longer than 256 word pieces are truncated by default |
| `bge` | `BAAI/bge-base-en-v1.5` | Common medium-sized retrieval model | 768 dimensions; query and document encoding policy must be explicit and consistent |
| `technical` | `jinaai/jina-embeddings-v2-base-code` | Technical/code-biased candidate | 161M parameters, long-input support, and `trust_remote_code=True`; compatibility and pinned revision require an implementation spike |

The aliases describe experimental roles, not expected winners. In particular,
`technical` must not be presented as “better” before it wins the local labelled
benchmark. ESP32 datasheets contain technical prose and tables, not only source
code, so this is a real domain-transfer test.

Before accepting the technical candidate, verify on the CPU-only Apple Silicon
container:

- installation and model loading with the pinned dependency versions
- model revision pinning and remote-code review
- embedding dimension and normalization
- memory usage, cold-load time, and throughput
- query/document encoding symmetry

Primary model references:

- [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [BGE base v1.5 model card](https://huggingface.co/BAAI/bge-base-en-v1.5)
- [Jina code embeddings model card](https://huggingface.co/jinaai/jina-embeddings-v2-base-code)

### Chunking strategies

| Alias | Strategy | Purpose |
| --- | --- | --- |
| `custom` | Existing sentence-oriented, table-aware PDF chunker | Domain-aware implementation under test |
| `recursive` | LangChain `RecursiveCharacterTextSplitter`, initially 500 characters with 100-character overlap | Conventional generic RAG-demo baseline |
| `raw500` | Exact sequential 500-character windows with no semantic boundary detection and no overlap | Deliberately simple control |

Use the standalone `langchain-text-splitters` package for `recursive`, then feed
its chunks into the same metadata and FAISS implementation as every other
strategy. LangChain recommends the recursive splitter for generic text and it
tries paragraph, newline, space, and character boundaries in order. This makes
it a fair library chunker comparison without replacing the rest of the stack.

Do not use a complete LangChain or LlamaIndex vector-store pipeline in this
experiment. Doing so would change multiple independent variables at once. A
full-framework retriever can be evaluated later as its own end-to-end system.

The three chunkers do not create equally sized or equally numerous chunks.
Report the actual chunk count, mean/median size, size distribution, overlap, and
index size alongside retrieval metrics. If size becomes a dominant confounder,
add a second size-controlled experiment rather than silently tuning one method
until it wins.

### Retrieval methods

Treat retrieval method as a separate axis:

| Alias | Meaning |
| --- | --- |
| `dense` | Original-space cosine similarity from the selected embedding index |
| `literal` | Transparent exact phrase/token matching over the selected chunk set |
| `hybrid` | A later, explicitly specified combination of dense and lexical ranks |

The initial literal baseline should be intentionally understandable:

1. exact normalized phrase matches first
2. then chunks containing all meaningful query tokens
3. then decreasing token coverage
4. deterministic source order as the final tie-breaker

If nothing matches, return no result. Zero-result queries demonstrate where
literal lookup cannot bridge vocabulary or paraphrasing. Return the existing
paragraph/display context around a matched chunk so result presentation remains
comparable.

BM25 is a useful later lexical baseline, but it is different from the proposed
literal control and should have its own name and recorded configuration.

The initial matrix therefore contains:

- 9 dense conditions: 3 models × 3 chunkers
- 3 literal conditions: 1 literal algorithm × 3 chunkers
- optional hybrid conditions only after dense and literal results are understood

## What The Scores Mean

Cosine similarity is useful for inspecting one model's neighbourhoods, but raw
cosine values are not a shared accuracy scale across different models. One model
may naturally produce a tighter similarity distribution than another. Do not
conclude that a model with a top score of `0.75` is more accurate than one with
`0.45` unless the retrieved evidence is labelled and the ranking is evaluated.

The per-question `0..1` value in the comparison chart should initially be
**reciprocal rank**:

```text
RR = 1 / rank of the first relevant result
```

Examples:

- relevant evidence at rank 1 → `1.0`
- rank 2 → `0.5`
- rank 3 → `0.333`
- absent from the evaluated result window → `0.0`

Mean Reciprocal Rank (MRR) is the average across questions. Also report:

- Recall@1, Recall@3, Recall@5, and Recall@10
- literal-query coverage and zero-result rate
- ingestion and query latency
- chunk count and FAISS size
- top-result cosine and score separation as diagnostics, not correctness metrics

Add nDCG only if the benchmark later uses graded relevance. Do not introduce an
LLM judge for retrieval relevance while a small human-labelled benchmark is
feasible.

## Ground Truth Before Model Comparison

`benchmark_queries.txt` is currently a repeatable query list, not an evaluation
dataset. The next implementation milestone is a versioned benchmark format such
as `benchmarks/esp32-retrieval-v1.yaml`.

Each case should contain at least:

```yaml
id: pull-up-resistor-value
question: What is the resistance of the internal pull-up resistor?
topic: electrical-characteristics
relevant_evidence:
  - document: esp32-wroom-32u_datasheet_en.pdf
    page: 26
    text_anchor: Resistance of internal pull-up resistor
```

Ground truth must refer to stable source evidence, not random chunk UUIDs. Chunk
boundaries intentionally vary between strategies. A retrieved chunk is relevant
when it overlaps a labelled evidence span or contains its validated text anchor.
If PDF extraction changes enough that an anchor cannot be resolved, benchmark
validation should fail and request human review rather than guessing.

Build an intentionally varied first set of roughly 20–30 questions:

- exact identifiers and quoted terminology
- paraphrases whose words do not appear literally in the evidence
- table-value questions
- broad conceptual questions
- ambiguous questions
- questions whose answer is absent from the corpus

Keep a few current questions for continuity, but rewrite vague cases when the
intended relevant evidence cannot be labelled unambiguously.

## Architecture Direction

The current schema assumes one active embedding model and places
`embedding_model` on each chunk. That does not represent the new experiment:
chunks belong to a chunking configuration, while vectors and FAISS indexes
belong to an embedding configuration.

Use one ingestion and evaluation pipeline with registries/configuration, not
nine copies of the code:

```text
PDF loader
  -> chunker registry (custom | recursive | raw500)
  -> chunk sets with stable source evidence metadata
  -> embedder registry (mini | bge | technical)
  -> one FAISS index per chunker/model pair
  -> retriever (dense | literal | later hybrid)
  -> benchmark evaluator
  -> JSON run artifact
  -> HTML explorer
```

Recommended persisted identities:

- document: source path plus content hash
- chunking configuration: strategy name plus all parameters and code/config version
- chunk: document identity, chunking configuration, source span, and text hash
- embedding configuration: model id, pinned revision, normalization, dimensions,
  maximum length, and query/document prefixes
- index: corpus fingerprint plus chunking and embedding configuration identities
- evaluation run: benchmark version plus retriever/index configuration and code revision

A future schema can separate these concepts into `documents`, `chunk_sets`,
`chunks`, `indexes`, and `indexed_chunks`. `indexed_chunks` should use a composite
identity such as `(index_id, vector_id)` because vector ids can repeat safely in
different indexes.

Store FAISS artifacts under explicit paths such as:

```text
storage/indexes/custom/mini.faiss
storage/indexes/custom/bge.faiss
storage/indexes/raw500/technical.faiss
```

The exact path can later include configuration hashes. SQLite remains useful for
inspectable metadata and mappings; adopting a LangChain splitter does not
require adopting its database or vector-store abstractions.

## Command-Line Direction

Keep model and chunker selectors strict and human-readable:

```bash
python -m rageval ingest --model mini --chunker custom
python -m rageval ingest --model all --chunker all
python -m rageval evaluate retrieval --all
python -m rageval visualize
```

Recommended behaviour:

- `--model` accepts only `mini`, `bge`, `technical`, or `all`
- `--chunker` accepts only `custom`, `recursive`, `raw500`, or `all`
- a targeted baseline remains the default for quick development
- an explicit `--all` command builds the expensive nine-index showcase matrix
- the command prints the resolved model revisions, chunker parameters, output
  paths, estimated work, and whether existing artifacts can be reused

Defaulting every ordinary ingestion to all nine conditions would make small
debugging iterations unnecessarily slow on the M1. Provide a dedicated
`scripts/build_experiment_matrix.sh` for the full presentation workflow instead.

During refactoring, preserve thin root-level compatibility wrappers until the
new commands are documented and verified. The Python module CLI should remain
usable on macOS, Linux, and Windows; shell scripts are conveniences, not the only
interface.

## Visualization Direction

The HTML should become an experiment explorer with three explicit controls:

1. embedding model: `mini`, `bge`, or `technical`
2. chunker: `custom`, `recursive`, or `raw500`
3. retriever: `dense`, `literal`, and later `hybrid`

Use large model buttons because model comparison is presentation-important, but
do not implement keyword search as an ambiguous on/off modification to cosine
similarity. It is a different ranking method and should be labelled as such.

The 3D plot should:

- fit PCA on corpus vectors and transform query vectors through the fixed axes
- report explained variance for the three displayed components
- display geometry for the selected embedding model and chunking strategy
- colour by original-space cosine similarity in dense mode
- highlight literal results in literal mode while stating that the background
  geometry still belongs to the selected embedding model
- preserve the warning that 3D position is explanatory, not an accuracy metric

Below the 3D view, add the actual evaluation display:

- per-question reciprocal-rank lines or dots on a shared `0..1` scale
- aggregate MRR and Recall@k
- filters that focus lines without hiding which configuration is active
- a failure inspector showing the expected evidence and retrieved top results
- latency, chunk count, and index-size tradeoffs

Do not compare models by raw cosine height across model families. Compare them
by labelled rank metrics, then use cosine distributions and the 3D view to
investigate why.

## Proposed Code And Documentation Layout

This is a direction, not a requirement to move every file in one commit:

```text
rageval/
  config/          model and chunker registries
  ingestion/       discovery and orchestration
  chunking/        custom, recursive, and raw500 adapters
  embeddings/      model adapter and query/document encoding policy
  storage/         SQLite metadata and FAISS artifact access
  retrieval/       dense, literal, and hybrid retrievers
  evaluation/      benchmark loading, relevance, metrics, and run artifacts
  visualization/   data export for the browser explorer
scripts/
  run_in_container.sh
  build_experiment_matrix.sh
  serve_visualization.sh
benchmarks/
docs/
tests/
```

Keep the public `README.md` short: goal, current implemented status, one quick
demo, one experiment-matrix command, and links into `docs/`. Stable detailed
notes should eventually be split into:

- `docs/architecture.md`
- `docs/chunking.md`
- `docs/embedding-models.md`
- `docs/retrieval-evaluation.md`
- `docs/visualization.md`
- `docs/local-workflow.md`

## Staged Implementation

### Phase 1: benchmark and contracts

- define and manually label the first benchmark cases
- add benchmark validation and relevance matching
- define typed model, chunker, retriever, and experiment configuration objects
- capture the current MiniLM/custom results as a regression baseline

### Phase 2: separate experiment identities

- separate chunks from embeddings in metadata
- support multiple chunk sets and indexes without overwriting active state
- use deterministic configuration identities and artifact manifests
- migrate by rebuilding ignored local storage, not by preserving obsolete random ids

### Phase 3: chunking matrix

- adapt the current chunker behind a small interface
- add raw 500-character chunking
- add only `langchain-text-splitters` and its recursive adapter
- produce chunk statistics and validate source-evidence mapping

### Phase 4: embedding matrix

- replace the hard-coded model constant with a registry
- implement model-specific query/document encoding policy
- add strict CLI selectors and explicit full-matrix build command
- benchmark CPU latency, memory, artifact size, and retrieval metrics

### Phase 5: lexical and dense evaluation

- add the literal retriever and zero-result behaviour
- persist ranked results and calculate RR, MRR, and Recall@k
- compare every condition using the same benchmark and top-k budget
- add hybrid retrieval only after the two baselines are understood

### Phase 6: visualization and documentation

- refactor visualization generation to consume saved evaluation runs
- add model, chunker, and retriever controls
- add per-query rank charts and failure inspection
- shorten the README and split stable documentation by concern
- record reproducible presentation commands and expected runtime

### Phase 7: return to answer evaluation

- use the best understood retrieval configurations in the no-context,
  retrieved-context, and oracle-context LLM experiment
- keep retrieval metrics separate from answer correctness and grounding metrics

## Definition Of A Convincing Result

The project succeeds even if the custom chunker or technical model does not win.
A convincing result is one where:

- the benchmark evidence is human-verifiable
- every condition changes one declared variable
- configuration and artifacts are reproducible
- ranking metrics support the claims
- the visualization helps explain failures without being treated as proof
- latency and storage costs are visible
- negative and zero-result cases remain in the report

That is a stronger engineering portfolio story than selecting the prettiest
embedding cloud or the model with the largest cosine values.
