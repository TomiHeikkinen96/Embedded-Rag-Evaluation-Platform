# Possible Future Directions

This is a design horizon, not a second status tracker. The living implementation
state and priorities are maintained only in [`todo.md`](../todo.md).

## Improve evidence selection

The immediate experimental direction is to spend prompt budget more carefully:

- compare literal, dense, and eventually hybrid retrieval
- compare the transparent lexical heuristic with a learned reranker
- add relevance filtering, dynamic top-k, and context compression
- measure answer quality, refusal, latency, and token cost together

This work should use the existing labelled corpus and saved-run discipline so a
new technique is not accepted merely because one demonstration looks better.

## Add a small product interface

A minimal REST API and TypeScript/React conversation UI could expose grounded
questions, citations, refusal, ingestion status, and usage metrics. Conversation
history would require explicit limits, summarization, retention, deletion, and
provenance rules rather than an unbounded list of messages.

This stage should preserve the current replaceable retrieval, prompt, provider,
and evaluation modules instead of hiding them behind a large framework.

## Compare a bounded agentic loop

The first agentic condition should answer a narrow experimental question: does
letting the model decide when and how to inspect the corpus improve results over
fixed retrieve-then-read RAG?

It could expose literal and dense retrieval as validated tools, cap calls and
returned text, persist observations, and allow a bounded refinement before the
model answers or refuses. The same model, questions, and scoring contract should
remain fixed so tool-selection and iteration are the variables being measured.

## Validate engineering outcomes

Later embedded tasks could be checked through increasingly strong evidence:

1. deterministic required-fact and static checks
2. compilation and unit or integration tests
3. simulator or hardware-in-the-loop observations
4. serial logs, timing, logic traces, or physical measurements
5. human engineering review where automation cannot establish behaviour

The goal would be to measure whether grounded context improves actual
engineering work, not merely whether an answer sounds plausible.

## Production hardening

A real multi-user service would need authentication, tenant and document
isolation, asynchronous ingestion, durable storage, secrets and privacy controls,
observability, cost limits, provider failure handling, evaluation gates,
deployment, scaling, migrations, and rollback. These concerns are deliberately
left outside the small local prototype but should be addressed before treating
it as a production feature.

## Non-goals

- claiming a generally superior coding agent from one corpus
- presenting framework integration as evidence of retrieval quality
- using an LLM judge as the only oracle
- hiding failed, ambiguous, or zero-result cases
- adding autonomy before its tools and observations can be measured
