# Local generation model

The first generation baseline uses Qwen 3.5 9B through Ollama. The checked-in
[`Modelfile`](../Modelfile) fixes a small, reproducible starting configuration;
it does not embed retrieval or tool behaviour into the model.

## Install Ollama on Apple Silicon

Install the command-line service with Homebrew:

```bash
brew install ollama
brew services start ollama
ollama --version
```

Ollama runs natively on macOS so it can use Apple Metal. Keep it outside the
project's Colima containers; containerized project code can call the host Ollama
API later.

Create the project model from the repository root:

```bash
ollama create rageval-qwen -f Modelfile
ollama run rageval-qwen
```

The first command downloads the Qwen 3.5 9B base model if necessary. Model data
is stored by Ollama outside this repository and is not committed.

After the model has been created, run the dependency-free Python smoke test:

```bash
python3 scripts/ollama_smoke_test.py
```

The script selects `rageval-qwen` in its API request, so `ollama run` does not
need to be running in another terminal. The Ollama service must be running;
it loads the selected model on demand. The script prints the prompt, response,
input and output token counts, wall-clock time, Ollama timings, model-load time,
and generation speed. To inspect Ollama's complete JSON response, run:

```bash
python3 scripts/ollama_smoke_test.py --show-json
```

For an interactive frontend-style response, stream generated text and report
time to first token:

```bash
python3 scripts/ollama_smoke_test.py --stream
```

Streaming improves perceived responsiveness, not generation speed. Keep the
non-streaming mode for simple repeatable evaluation; Ollama reports final token
counts and timing metrics after either request completes.

## Ask a grounded question

After the Arctic index and `rageval-qwen` model exist, run the first end-to-end
RAG command:

```bash
./ask_question.sh "What voltage and maximum output current can the ESP32 built-in flash voltage regulator supply?"
```

The command loads the native Arctic Embed index, retrieves three excerpts,
builds source-labelled context, streams the answer from Ollama, prints only the
sources Qwen cited, and reports retrieval, token, and generation metrics. Useful
inspection options are:

```bash
./ask_question.sh --show-context "question"
./ask_question.sh --no-stream "question"
./ask_question.sh --embedding bge "question"
```

This is the interactive dense-RAG path. Its default generation and retrieval
choices are deliberately fixed to `rageval-qwen` and `arctic`.

## Run the generation benchmark

Run all committed cases through closed-book, oracle, and Arctic dense-RAG
conditions:

```bash
./run_generation_eval.sh
```

No arguments produces the canonical baseline. For a quick development check,
filter by case or condition; the resulting manifest is marked non-canonical:

```bash
./run_generation_eval.sh --case flash-voltage-regulator --condition oracle
./run_generation_eval.sh --case out-of-domain-cookie-recipe --condition dense_rag:arctic

# Compare Arctic generation with ten retrieved excerpts; leaves the canonical
# top-three benchmark unchanged.
./run_generation_eval.sh --condition dense_rag:arctic --top-k 10
```

The evaluator uses non-streaming responses so each completed result is written
atomically to `runs/generation/<timestamp>/results.jsonl`. The same directory
also contains the resolved `manifest.json` and aggregate `summary.json`.

Useful checks:

```bash
ollama list
ollama ps
curl http://localhost:11434/api/tags
```

`ollama ps` shows the allocated context and whether the model is using the GPU.
Stop the loaded model without stopping the service with:

```bash
ollama stop rageval-qwen
```

## What the Modelfile controls

The initial definition selects `qwen3.5:9b`, an 8K context, low-variance
sampling, and a short system instruction that requires abstention when the
available information is insufficient. These settings should be recorded with
every experiment and changed deliberately.

The Modelfile does **not** give the model access to files, search, FAISS, or
shell commands. Ollama can be called as a normal chat model without tools. Tool
definitions and the loop that executes approved tool calls are supplied by the
future harness, so the same model can be evaluated fairly in every condition.

## First generation comparison

The current baseline runs the same questions, model definition, scoring rules,
and limits in three evidence-access conditions:

1. **Closed-book:** no corpus or tools. This measures model prior knowledge and
   hallucination or appropriate abstention.
2. **Oracle context:** the harness supplies the human-verified evidence. This
   separates retrieval failure from the model's ability to use correct context.
3. **Dense RAG:** the harness supplies top-k evidence from the existing
   retrieval pipeline; the model does not choose the evidence.

A bounded grep agent is the next planned condition. It will be intentionally
agentic while dense RAG is not. A later condition can let the model decide when
to call dense retrieval, but it should not replace the simpler comparison.

Start with narrow questions whose answers can be checked without another LLM:

- boolean capability questions: supported, unsupported, or unknown
- exact-value questions with normalized units
- exact identifiers, register names, limits, and enumerated modes
- corpus-negative questions where the correct result is `unknown`

Store a typed expected answer and acceptable variants for each case. The current
runner scores normalized required facts, abstention, citation labels, and
evidence-page retrieval. Unsupported extra claims remain a manual review item
until a reliable claim-level check is added. Latency and tool-call count are
secondary measurements.

This first slice asks a focused question: does the small model already know the
answer, can cheap literal inspection supply it, does dense retrieval improve it,
and can it answer when guaranteed to receive the correct evidence?
