# RAGeval presentation draft
Personal working notes for a technical interview. The final slide deck is not included in this public repository and may be shared privately on request after the interview.

## Presentation goal

Prepare a ten-minute core presentation for a technical interview audience, with
enough optional detail to expand naturally toward the requested fifteen-minute
demo.

By the end, the audience should understand why the project exists, how the
local retrieve-then-read pipeline works, what the evaluation demonstrated, how
AI-assisted development was controlled, and what would be required to turn the
prototype into a product.

The presentation should be high-level and visual. The slides establish the
story and vocabulary; the terminal, repository, and evaluation explorer provide
the technical zoom.

Core takeaway:

> Correct evidence made a small local model substantially more reliable, but
> retrieval depth introduced measurable context, latency, and review costs.

## Ten-minute structure

| Time | Section |
| --- | --- |
| 0:00-0:45 | Slide 1: problem and project question |
| 0:45-1:45 | Slide 2: high-level architecture |
| 1:45-2:35 | Slide 3: evaluation design |
| 2:35-3:50 | Slide 4: findings and top-k trade-off |
| 3:50-7:15 | Live demo and repository tour |
| 7:15-8:20 | Slide 5: AI-native development workflow |
| 8:20-9:40 | Slide 6: product direction |
| 9:40-10:00 | Closing statement and buffer |

The interview brief permits fifteen minutes. A rehearsed ten-minute core leaves
room for model latency, transitions, questions, or one optional technical zoom.

---

## Slide 1 — Can a small local model answer version-specific hardware questions?

### Narrative job

Explain why the project exists and give the audience a calm overview of what is
coming.

### Visible content

Title:

> Can a small local model answer version-specific hardware questions?

Subtitle:

> A local RAG and evaluation harness for ESP32 documentation

Small navigation line at the bottom:

> Problem → pipeline → evidence → live inspection → product path

### Visual

Use a crop or composition of the actual ESP32 manuals with one small factual
passage highlighted. Avoid a generic robot, AI brain, or stock photograph. The
visual should communicate that the answer exists, but is buried inside large,
revision-specific documentation.

### Speaker notes

- Embedded development depends on datasheets, reference manuals, errata, SDK
  documentation, and knowledge held by experienced engineers.
- A model may know common ESP32 facts, but that does not establish whether it is
  using the correct device, revision, page, or operating condition.
- This project tests whether supplying correct context improves answers,
  citations, and refusal behaviour when using a deliberately small local model.
- RAG only retrieves knowledge that has been written down; it does not magically
  recover genuinely unwritten tribal knowledge.
- In the next few minutes: the pipeline, the experiment, the result, a live
  answer, the development workflow, and the product direction.

### Transition

> To test the value of context, I first needed a pipeline where every stage was
> simple enough to inspect.

---

## Slide 2 — The pipeline keeps retrieval, generation, and evaluation inspectable

### Narrative job

Show that the assignment's complete RAG path exists without turning the slide
into a source-code diagram.

### Visible content

Use one left-to-right pipeline with short labels:

> Local PDFs → clean and chunk → embed and index → retrieve and rerank → bounded
> context → local Qwen → citation or refusal

Add a smaller evaluation branch underneath:

> Golden questions and evidence → compare conditions → saved, reviewable runs

Small technology labels can sit beneath the relevant stages:

- custom PDF chunking
- MiniLM / BGE / Arctic
- FAISS + SQLite
- Ollama + Qwen 3.5 9B

### Visual

Use a single simple architecture diagram. Keep ingestion, question answering,
and evaluation visually distinct, but do not show every Python module.

Suggested structure:

```text
INGESTION
PDFs → clean/chunk → embeddings → FAISS vectors + SQLite metadata

QUESTION
Question → retrieve/rerank → labelled context → local Qwen → answer/refusal

EVALUATION
Fixed questions + gold evidence → condition comparison → saved artifacts
```

### Speaker notes

- PDFs are loaded locally and split into sentence-oriented, first-pass
  table-aware chunks with source and page metadata.
- Embeddings and generation remain local. Arctic ingestion and question
  answering can use Apple MPS; Docker remains the portable CPU workflow.
- FAISS performs vector similarity search. SQLite keeps the chunks, source
  metadata, and explicit vector-to-chunk mapping inspectable.
- Retrieval applies a deliberately transparent heuristic reranker: semantic
  similarity plus modest token overlap, penalties for contents-like material,
  and paragraph deduplication.
- The selected excerpts are labelled `S1`, `S2`, and so on before being sent to
  Qwen through Ollama.
- The prompt requires grounded factual claims, citations, and a clear refusal
  when the supplied documents do not establish an answer.
- The CLI is intentional. A UI or API would not improve the central experiment,
  and the assignment explicitly allows a CLI.

### Assignment coverage

This slide visually covers all seven requested application capabilities:

1. load local documents;
2. split them into chunks;
3. create embeddings;
4. store and retrieve chunks;
5. send retrieved context to an LLM;
6. return citations;
7. refuse unsupported questions.

### Transition

> A working pipeline is easy to demonstrate with one favourable question. The
> harder question is whether retrieval actually changes model behaviour.

---

## Slide 3 — Three conditions isolate where failures happen

### Narrative job

Explain the evaluation design before showing the dashboard or its metrics.

### Visible content

Show three parallel lanes feeding the same model and the same questions:

### Closed book

> No documents
> What does the model already know?

### Oracle context

> Manually verified evidence
> Can the model use the right context?

### Dense RAG

> Retrieved Arctic chunks
> Can the pipeline find and use the evidence?

End all three lanes at the same compact outcome labels:

> Required facts · refusal · citations · evidence hit · tokens · latency

### Visual

Use three wide horizontal lanes rather than a table. Oracle should be visually
positioned as the diagnostic ceiling, not as a production option.

### Speaker notes

- Every condition uses the same seven typed questions and the same local Qwen
  model settings.
- Five questions are answerable and two are corpus-negative controls.
- Closed book measures model prior knowledge.
- Oracle context separates generation capability from retrieval failure. If
  oracle fails, retrieval alone cannot solve the problem.
- Dense RAG measures the actual retrieve-then-read pipeline.
- Required-fact checks detect whether expected facts are present. Citation and
  refusal checks enforce the response contract.
- Raw answers are retained because substring checks cannot establish whether
  every additional free-form claim is supported or non-contradictory.
- Unit tests cover prompt construction, stable source labels, citation parsing,
  refusal and fact scoring, benchmark configuration, aggregation, partial-run
  recovery, and explorer export.
- Labelled retrieval and generation benchmarks provide repeatable behavioural
  checks beyond the unit tests.

### Transition

> The comparison showed both why context matters and why simply retrieving more
> context is not a free improvement.

---

## Slide 4 — Better context improved correctness, but context depth had a cost

### Narrative job

Turn the main evaluation table into one memorable engineering finding.

### Visible content

Do not paste the dashboard table onto the slide. Use two clean visuals.

### Left visual: condition comparison

Use three vertical bars for overall contract pass rate:

| Condition | Overall contract |
| --- | ---: |
| Closed book | 0.0% |
| Arctic RAG, top 3 | 71.4% — 5/7 |
| Oracle context | 100.0% — 7/7 |

Short interpretation beneath the chart:

> The model could use correct evidence; the remaining gap was retrieval and
> context selection.

### Right visual: experimental retrieval-depth comparison

Show top 3 and top 10 as two endpoints connected by an arrow:

| Metric | Top 3 | Top 10 |
| --- | ---: | ---: |
| Overall contract | 5/7 | 7/7 |
| Gold evidence | 80% | 100% |
| Average total tokens | 1,664 | 5,339 |
| Average pipeline time | 24.75 s | 53.11 s |

Large takeaway:

> Two additional passes cost 3.2× the tokens and 2.1× the pipeline time.

Use “context cost” or “compute and latency cost,” not direct monetary cost,
because the current model runs locally.

### Required footnote

> Seven-case ESP32 benchmark. Top 3 is the committed baseline; top 10 is a
> filtered, non-canonical experiment. Automated checks cover required facts,
> refusal intent, and citations; unsupported extra claims still require manual
> review.

### Speaker notes

- Closed book produced some expected words, but did not satisfy the grounded
  answer contract. This is a useful example of plausible model knowledge not
  being the same as reliable evidence.
- Oracle reached 100%, showing that the small model can answer these cases when
  supplied with verified evidence.
- Arctic RAG at the committed top 3 reached 5/7 and retrieved gold evidence for
  80% of the relevant cases.
- The top-10 experiment recovered the two remaining cases on this small
  benchmark, but average context grew substantially and generation took longer.
- This does not prove that top 10 is universally better. It motivates learned
  reranking, relevance gating, dynamic top-k, and context compression.
- The result is an engineering trade-off, not a claim of perfect RAG.

### Transition into the live demo

> Those percentages are the summary. I want to show what one answer actually
> looks like and what the model was allowed to see.

---

## Live demo — Inspect one answer end to end

Target duration: three to four minutes.

### Prepare before presenting

- Start Ollama and warm the `rageval-qwen` model.
- Confirm the Arctic index exists.
- Use a large terminal font and a clean terminal window.
- Open the frozen evaluation explorer in advance and select the relevant run.
- Keep the repository README open in a separate browser tab.
- Do not run ingestion live; explain that the corpus has already been indexed.
- Do not depend on Docker, model downloads, or network access during the demo.

### Step 1: show that the workflow is approachable

Spend roughly fifteen seconds on the README quickstart:

```bash
./local_ingest_data.sh --model arctic
./ask_question.sh "question"
```

Say:

> The public workflow is intentionally two task-oriented commands: ingest the
> documents, then ask a grounded question. The detailed model and clean-rebuild
> options are documented but do not dominate the quickstart.

### Step 2: inspect a grounded answer

Run:

```bash
./ask_question.sh --show-context \
  "What voltage and maximum output current can the ESP32 built-in flash voltage regulator supply?"
```

Point out only four things:

1. the top retrieved excerpt from the ESP32 Technical Reference Manual;
2. the expected `3.3 V`, `1.8 V`, and `40 mA` facts;
3. the `[S1]` citation and source page;
4. retrieval time, prompt/output tokens, and generation timing.

Avoid explaining every printed field. The purpose is to show that the answer is
traceable to exactly what entered the prompt.

### Step 3: demonstrate refusal

If timing and model stability allow, run:

```bash
./ask_question.sh \
  "Which ESP32 GPIO pins provide the native USB D+ and D- interface?"
```

The current ESP32 corpus does not establish an answer, so the expected behaviour
is a refusal rather than borrowing facts from another ESP32-family device.

If the live response is slow, show the saved evaluation case instead. The goal
is to demonstrate behaviour, not prove that a local model can type quickly.

### Step 4: open the evaluation explorer

Show only the condition comparison and top-k comparison used on Slide 4.

Say:

> The explorer is not the application UI. It is an engineering review surface:
> every aggregate can be traced back to retrieved excerpts, raw answers, token
> counts, and saved run configuration.

Do not tour every graph. Mention that retrieval rankings, distractor intrusion,
and per-question failures are available for follow-up.

### Optional repository zoom

If there is an extra minute, briefly show:

- `AGENTS.md` as the stable agent-development contract;
- `benchmarks/esp32-generation-v1/experiment.json` as evaluation-as-code;
- `tests/` as the deterministic unit-test boundary;
- `todo.md` as the only living priority and limitation list.

---

## Slide 5 — The repository itself was the agent-development harness

### Narrative job

Answer the assignment's AI spec, implementation-process, and review questions
without presenting AI generation as either magic or something to hide.

### Visible content

Use one iterative loop:

> Human scope and decisions → repository guidance → AI implementation → tests
> and evaluation → manual Git review → repeat

Small labels under “repository guidance”:

> `AGENTS.md` · focused design docs · benchmark JSON · `todo.md`

Small ownership line:

> AI generated most implementation and documentation. Human review retained
> architecture, trade-offs, boundaries, and acceptance decisions.

### Speaker notes

#### What spec or prompt drove implementation?

- There was not one disposable mega-prompt.
- The initial requirements and architecture were discussed with an agent and
  turned into `AGENTS.md` and focused design documents.
- The repository then became the persistent specification: stable boundaries in
  `AGENTS.md`, executable experiment settings in benchmark JSON, detailed design
  in `docs/`, and current intent in `todo.md`.
- Individual tasks followed an “ask first, implement second” conversation: walk
  through architectural questions, choose a direction, then let the agent make
  a scoped change.

#### How was the work broken into small steps?

1. PDF loading, chunking, SQLite metadata, FAISS, and local search.
2. Explicit vector-to-metadata identity and inspection tools.
3. Multiple embedding models and labelled retrieval questions.
4. Wrong-device distractors and retrieval visualisation.
5. Local Qwen generation with citations and refusal.
6. Closed-book, oracle, and dense-RAG comparison.
7. Token, latency, top-k, partial-run, and frozen-demo reporting.

Each step left the pipeline usable and produced evidence for the next decision.

#### What did AI generate, and what did the human review?

- AI generated most code and documentation and ran the available validation.
- The human retained ownership of the problem, architecture, scope, trade-offs,
  guardrails, and final acceptance.
- Every proposed change was manually reviewed through Git.
- Benchmark questions and scope evolved deliberately as evaluation exposed
  ambiguity.
- The Jina-to-Arctic change is one example: Jina worked on CPU, but its custom
  code crashed on native MPS. The implementation changed only after observing
  and reviewing that incompatibility.

#### How was behaviour tested?

- deterministic unit tests for prompts, citations, refusal scoring,
  configuration, aggregation, recovery, and export;
- locked corpus hashes plus labelled document/page/text evidence;
- retrieval metrics and distractor analysis;
- fixed closed-book, oracle, and dense-RAG generation cases;
- saved raw outputs, resolved manifests, tokens, and latency for manual review.

### Transition

> The same discipline also makes the next work clear: improve the experiment
> before adding autonomy or production surface area.

---

## Slide 6 — A product must select less, serve safely, and act with evidence

### Narrative job

Answer “what would you do next?” with three architectural directions rather
than a long feature backlog.

### Visible content

Use three large steps or columns with only these headings and short supporting
phrases.

### 1. Select less

> Learned reranking · relevance gating · dynamic top-k · context compression

Purpose:

> Keep the useful evidence while reducing irrelevant tokens and latency.

### 2. Serve safely

> REST API · conversation UI · explicit memory policy · authentication · tenant
> isolation · privacy controls

Purpose:

> Turn the CLI into a multi-user feature without leaking documents or history.

### 3. Act with evidence

> Bounded agentic loop · tool permissions · builds and tests · device output ·
> continuous evaluation gates

Purpose:

> Let the system decide when to retrieve or verify while keeping actions
> observable and constrained.

### Speaker notes

- The first next experiment should address the demonstrated top-k trade-off,
  rather than immediately adding a framework or autonomous loop.
- An API and conversation UI introduce explicit memory questions: what is
  retained, for how long, for which user and tenant, and whether old context is
  still valid.
- Multi-tenant retrieval requires authorization-aware document filtering before
  context reaches the model, not merely filtering citations afterward.
- A production agentic loop should be bounded by allowed tools, budgets,
  stopping rules, auditability, and repeatable evaluation.

### Closing statement

> This is not a claim that RAG is solved. It is a small, inspectable system for
> measuring when context helps, when retrieval fails, and what better grounding
> costs.

Do not end on a generic “Thank you” slide. Leave this final synthesis visible
during the transition into questions.

---

## How the presentation answers the interview brief

| Requested discussion | Where it is answered |
| --- | --- |
| AI spec or prompt | Slide 5: repository guidance and speaker notes |
| Small implementation steps | Slide 5: seven incremental slices |
| AI-generated versus human-reviewed work | Slide 5: ownership split and Git review |
| Testing retrieval and generation | Slides 3-4, live explorer, and Slide 5 notes |
| Production improvements | Slide 6 |
| Complete seven-stage RAG application | Slide 2 and live demo |
| Citations and unsupported-answer refusal | Slide 2 and live demo |
| Design choices and trade-offs | Slides 2-4 and Slide 6 |

## Optional five-minute expansion

Use these only if the core demo finishes early or the interviewer invites more
detail:

1. Show one failed top-3 case and the top-10 evidence that recovered it.
2. Explain why oracle context is a diagnostic boundary rather than a production
   feature.
3. Open `experiment.json` and a saved run manifest to demonstrate reproducible
   configuration.
4. Show the explicit FAISS-vector-to-SQLite-chunk mapping.
5. Discuss why the current heuristic reranker is inspectable but not a learned
   relevance classifier.
6. Explain how tenant-aware retrieval and document ACLs would fit a long-lived
   multi-tenant SaaS architecture.

## Likely follow-up discussion points

### Why not LangChain or an agent framework?

The experiment needed a transparent retrieve-then-read baseline. A framework
would be justified when it removes demonstrated complexity or when comparing
implementations, not merely to make the prototype appear more advanced.

### Why FAISS plus SQLite?

FAISS keeps local similarity search small and fast. SQLite keeps chunk text,
source metadata, and vector identity inspectable. A production system would
reconsider durability, concurrency, tenant filtering, access control, and
managed operations.

### Why three embedding models?

MiniLM provides a small fast baseline, BGE an established retrieval baseline,
and Arctic a retrieval-focused model with a repeatable native MPS path. The
comparison uses strict aliases over the same corpus and labelled questions.

### What guardrails exist now?

Bounded source-labelled context, instructions to treat excerpts as data,
citation validation, and explicit refusal behaviour. Missing production layers
include PII detection or redaction, document-level authorization, prompt-
injection handling, audit policy, and tenant isolation.

### What are the limitations of the current metrics?

- Seven generation cases are useful evidence, not statistical proof.
- Required-fact checks measure presence and can miss contradictory extras.
- Citation validity establishes that labels exist, not that every claim is
  entailed by a citation.
- Target-document precision is not identical to exact passage relevance.
- Timing varies with model warmth, prompt length, and local hardware.

## Visual and delivery guidance

- Use a restrained technical palette with one accent colour for verified
  evidence and one contrasting colour for cost or uncertainty.
- Prefer actual repository evidence: a manual-page crop, architecture diagram,
  clean charts derived from saved results, terminal output, and the evaluation
  explorer.
- Avoid screenshots containing the entire dashboard table; recreate only the
  numbers needed for the current claim.
- Keep slide titles as conclusions, not topic labels.
- Use at least 35 pt slide titles and 16 pt body text; shorten copy before
  shrinking fonts.
- Keep code off the slides. Show commands and implementation details in the live
  terminal or repository.
- Use presenter notes for timing and implementation detail; do not expose
  rehearsal instructions on audience-facing slides.
- Rehearse the transition into and out of the live demo so the browser and
  terminal do not feel like a context switch.

## Demo safety checklist

- [ ] Ollama is running and the model is warm.
- [ ] Arctic index and `.venv` are present.
- [ ] Grounded-answer command has been tested immediately before the interview.
- [ ] Frozen evaluation explorer opens without Docker or network access.
- [ ] Terminal font is readable from screen sharing.
- [ ] Browser zoom is appropriate for the dashboard.
- [ ] Correct run and condition are preselected.
- [ ] No private PDFs, absolute paths, or unrelated terminal history are visible.
- [ ] A saved answer is available if live generation stalls.
- [ ] The ten-minute core has been rehearsed without optional material.
