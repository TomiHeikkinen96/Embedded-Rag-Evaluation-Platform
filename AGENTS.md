# AGENTS.md

This is the instruction file future coding agents should read first in this repository.

## Project Idea

This project is a local context-engineering and evaluation harness for embedded software work, using ESP32 documentation as the current source corpus.

The point of the repo is not just to "make search work." The repo exists to evaluate whether better hardware-grounded context leads to better AI-assisted engineering outcomes: better answers, fewer hallucinations, and more useful embedded-development support.

That means changes should favor:

- repeatability
- inspectability
- simple local workflows
- clear experimental tradeoffs
- architecture that is easy to reason about and modify

## Current Architecture

Keep the current module boundaries explicit and understandable:

- `scripts/ingest.py` orchestrates discovery, change detection, chunking, embedding, SQLite updates, and FAISS rebuilds
- `scripts/search_index.py` performs local query embedding, FAISS lookup, and result rendering
- `scripts/chunkers/` owns chunking logic
- `scripts/processing/` owns document loading and embedding concerns
- `scripts/utils/db.py` owns SQLite access and schema helpers
- `scripts/utils/hashing.py` owns file hashing
- `scripts/generation/` owns grounded prompt construction and the narrow Ollama provider
- `scripts/answer_question.py` composes retrieval and generation for one grounded answer
- `scripts/evaluation/` owns generation benchmark loading, evidence conditions, scoring, artifacts, and aggregation
- `scripts/run_generation_eval.py` runs the versioned generation experiment
- `scripts/visualization/` exports retrieval and generation results for the evaluation explorer
- root shell scripts expose the supported task-oriented Docker and native local workflows

The current implementation is intentionally local-first and intentionally simple. Do not add unnecessary abstraction, framework-style indirection, or premature generalization.

## Coding Priorities

Optimize for human readability first.

Preferred style:

- small functions with one clear job
- explicit data flow over cleverness
- obvious naming over short naming
- straightforward control flow over compact tricks
- modular changes that preserve clean boundaries between ingestion, chunking, storage, and retrieval

Avoid:

- hidden coupling between FAISS ordering and SQLite ordering unless it is made explicit and well-documented
- mixing search logic, storage logic, and presentation logic in one place
- broad refactors that make the experiment harder to inspect
- adding complexity only to make the code feel more "production-like"

When making architectural changes, prefer the smallest change that makes the system more reliable and easier to understand.

If the codebase starts getting messy, larger refactors are acceptable when they materially improve readability, modularity, and flow. Do not refactor just because the project is under source control; refactor when the result is clearly easier for humans to understand and maintain. If a bigger refactor seems justified, explain the tradeoff to the user clearly.

## Documentation, Retrieval, and Evaluation Direction

`README.md` is the public source of truth for what the project is, what is
currently demonstrable, and how a new user gets started. Keep it accurate and
portfolio-readable. Do not turn it into a detailed engineering log or present
planned work as implemented.

`todo.md` is the only living implementation-status, limitation, and priority
list for this repository.

Agents should read `todo.md` before starting substantial work, use it to understand current priorities, and update or improve it when that would make the next steps clearer. The goal is to keep task tracking in one place instead of rewriting the todo list inside `AGENTS.md`.

When investigation produces meaningful findings, record them in `todo.md`. Do not limit updates to unchecked boxes only; use the file as a concise engineering log for completed work, open questions, and recommended next steps.

Detailed design explanations and experiment specifications belong in `docs/`.
They should describe current behavior or preserve a comparison design without
maintaining a second status checklist. `docs/README.md` is the documentation
index, and `docs/roadmap.md` is a design horizon rather than a task tracker.

`docs/retrieval-pipeline.md` is the short reference note for the current retrieval design.
If retrieval behavior, scoring, chunking, or display-context logic changes in a meaningful way, keep that document aligned with the code. Do not let it drift into a stale theory document.

`docs/evaluation.md` describes the separation between retrieval and generated-answer evaluation. Keep retrieval evidence metrics, answer-contract checks, and unsupported-claim limitations explicit rather than collapsing them into one apparent quality score.

## Working Rules for This Repo

- Preserve the local-first nature of the demo.
- Keep dependencies justified and minimal.
- Prefer incremental improvements over big rewrites.
- If a tradeoff is experimental, document it clearly in code, `todo.md`, or the appropriate focused document; keep the public summary in `README.md` aligned without moving every experiment into it.
- When changing schemas or indexing behavior, keep the mapping between stored metadata and retrieval results explicit.
- If a change affects retrieval quality, add a simple way to inspect or validate the impact.
- Prefer reusable local inspection tools over long one-off shell commands when the same debugging task is likely to recur.
- If a debugging workflow becomes awkward, standardize it in a small script with clear parameters rather than repeating ad hoc command snippets.

## Validation Expectations

- Run the smallest relevant unit-test set for the changed behavior; run the full
  standard-library suite with `python -m unittest discover -s tests -v` when the
  change crosses prompt, scoring, artifact, or visualization boundaries.
- Run `scripts/validate_benchmark.py` when retrieval labels, corpus metadata,
  source loading, page handling, or evidence matching changes.
- Keep retrieval validation separate from generated-answer validation. A good
  final answer does not prove that retrieval found the labelled evidence, and a
  retrieval hit does not prove that the model used it correctly.
- For documentation-only changes, check local links and run `git diff --check`.
- Report exactly what was validated. Do not claim end-to-end, browser, model, or
  hardware coverage from narrower structural or unit checks.

## Notes for Future Changes

This repo is an experimentation platform, not just an application. Good changes make it easier to answer questions such as:

- What changed?
- Why did retrieval improve or regress?
- Which component caused the change?
- Can the result be reproduced locally?

If a proposed change makes those questions harder to answer, it is probably the wrong change for this repository.
