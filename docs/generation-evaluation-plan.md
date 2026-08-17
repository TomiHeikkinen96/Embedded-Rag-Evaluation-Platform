# Generation evaluation plan

This note preserves the implementation sequence after the first grounded-answer
command. The objective is evaluation as code: a committed experiment definition
runs the same cases and settings, records every attempt, and produces comparable
summaries.

## Supported commands

The interactive application uses one deliberate default retrieval path:

```bash
./ask_question.sh "What maximum output current can the flash regulator supply?"
```

Its defaults are the `rageval-qwen` Ollama model, the `arctic` embedding index,
top-three retrieval, streaming output, grounded citations, and timing/token
metrics.

The implemented baseline benchmark requires no arguments:

```bash
./run_generation_eval.sh
```

No arguments means: load the committed experiment specification and run all
currently declared cases and conditions. Optional repeatable `--case` and
`--condition` selectors are development filters. Filtered runs are marked
non-canonical in their manifest.

The committed baseline keeps dense retrieval at top-three. To compare Arctic at
top-ten without changing that baseline, run only the retrieval-dependent
condition with an explicit override:

```bash
./run_generation_eval.sh --condition dense_rag:arctic --top-k 10
```

The override is recorded as `top_k: 10` in the run manifest and marks the run
non-canonical. Closed-book and oracle do not retrieve, so rerunning them for this
comparison would add time without measuring the effect of retrieval depth.

## Current baseline matrix

The implemented `esp32-generation-v1` specification contains:

| Run identity | Evidence supplied to Qwen |
| --- | --- |
| `closed_book` | none |
| `oracle` | committed human-verified source excerpts |
| `dense_rag:arctic` | top-three Arctic Embed FAISS results |

## Expansion matrix

The generation model, prompt, questions, context budget, top-k, scoring policy,
and repetition count remain fixed. Only evidence access changes:

| Run identity | Evidence supplied to Qwen |
| --- | --- |
| `closed_book` | none |
| `literal` | fixed literal-search results |
| `dense_rag:mini` | MiniLM FAISS results |
| `dense_rag:bge` | BGE FAISS results |
| `dense_rag:arctic` | Arctic Embed FAISS results |
| `oracle` | human-verified benchmark evidence |

Embedding selection applies only to `dense_rag`. Closed-book, literal, and
oracle runs must not be duplicated under meaningless embedding labels.

The initial comparison is non-agentic so it isolates evidence quality. A later
`tool_agent` condition may let Qwen choose bounded literal or semantic search;
that condition measures tool selection and iteration as well as retrieval.

## Versioned specification

Add a generation benchmark beside the retrieval benchmark:

```text
benchmarks/esp32-generation-v1/
  cases.json
  experiment.json
```

`experiment.json` owns the canonical model, conditions, dense embedding models,
top-k, repetitions, prompt version, timeout, and context limits. `cases.json`
owns typed expected answers, acceptable normalized values or units,
answerability, and verified evidence references.

## Runtime components

Keep the implementation small and replaceable:

```text
scripts/generation/
  ollama_provider.py       # chat transport and usage metrics
  prompt_builder.py        # grounded messages and source labels

scripts/evaluation/
  conditions.py            # closed, literal, dense, oracle, later tool agent
  runner.py                # cases x conditions x repetitions
  scoring.py               # deterministic answer/citation/refusal checks
  artifacts.py             # manifest, JSONL attempts, aggregate summary

scripts/run_generation_eval.py
run_generation_eval.sh
```

The interactive command and evaluator must reuse the same Ollama provider,
prompt builder, retrieval path, and answer contract. The shell wrappers only
locate the project environment and forward arguments; experiment behaviour
belongs in Python and the committed specification.

## Artifacts

Each evaluation creates an ignored directory such as:

```text
runs/generation/2026-08-17T12-00-00Z/
  manifest.json
  results.jsonl
  summary.json
```

The manifest records resolved configuration, input-file hashes, and whether the run is canonical.
JSONL stores each completed attempt immediately so interrupted runs retain
evidence. The summary aggregates answer accuracy, correct refusal, retrieval
evidence hits, valid citations, latency, token use, tool calls, parsing errors,
and runtime failures.

The shared visualization exporter treats these artifacts as immutable. It uses
the saved summary for finalized runs and derives a temporary summary directly
from JSONL when a run was interrupted. Historical answers are never silently
rescored after benchmark labels change.

## Implementation checkpoints

1. [x] Complete `ask_question.sh` with Arctic retrieval, grounded prompting, Qwen,
   citations, refusal instructions, and usage metrics.
2. [x] Define typed generation cases by selecting narrow boolean, exact-value,
   identifier, and unanswerable cases from the retrieval benchmark.
3. [x] Add the committed experiment specification and common run-result schema.
4. [x] Implement closed-book and oracle conditions first; save JSONL attempts.
5. [x] Add deterministic answer normalization, refusal, and citation scoring.
6. [x] Add dense-RAG evaluation for Arctic. Next expand it across all registered
   embedding indexes without duplicating embedding-independent conditions.
7. Add fixed literal retrieval and generate the first canonical summary.
8. Add repetitions and explicit seeds for robustness runs.
9. Only then add a bounded structured-tool condition. Validate tool names and
   arguments, cap calls and returned text, and never execute model-authored shell.
10. Consider LangChain as a comparison adapter and MCP only if tools need to be
    exposed to external clients. Neither is required by the core harness.
