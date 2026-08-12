# Evaluation

The project evaluates layers separately so a successful-looking answer does not
hide a retrieval failure, and a retrieval failure is not blamed on the language
model.

## Retrieval evaluation — current focus

The planned benchmark labels the source evidence needed for each question. A
retriever is then measured by whether that evidence appears in its ranked
results.

Initial metrics:

- Recall@1, Recall@3, Recall@5, and Recall@10
- reciprocal rank per question and mean reciprocal rank (MRR)
- zero-result rate for literal search
- ingestion time, query latency, chunk count, and index size

Cosine similarity is a diagnostic, not correctness. Raw cosine values should
not be compared as if they were a universal accuracy score across embedding
models.

The first comparison matrix will vary:

- chunking: custom, recursive-character baseline, and raw 500-character windows
- embeddings: small general, medium retrieval, and technical/code-biased models
- retrieval: dense cosine and literal search, with hybrid retrieval considered later

See the [detailed plan](retrieval-evaluation-plan.md).

## Ground truth

Labels should identify durable evidence using document, page, and verified text
anchors—not random chunk ids. Chunk boundaries change between strategies, while
the underlying evidence does not.

The benchmark should contain exact terms, paraphrases, table questions, broad
questions, ambiguous questions, and questions not answered by the corpus.
Negative cases and failures remain visible in reports.

## Grounded generation — planned

Each engineering question will later be run under comparable context conditions:

1. no external context
2. retrieved context
3. manually verified oracle context

This separates three failure modes:

- the retriever did not find the evidence
- the model could not solve the task
- the model received evidence but used it incorrectly

Candidate generation systems may include a locally runnable coding model and
hosted APIs. They should share benchmark cases and recorded configuration rather
than being compared through hand-picked demonstrations.

## Validation ladder — planned

Generated embedded work needs stronger evidence than fluent text:

1. deterministic static checks and required-fact checks
2. compilation and unit/integration tests
3. simulator or hardware-in-the-loop observations where feasible
4. human engineering review for behaviour not established automatically
5. optional LLM review as an additional signal, never the sole oracle

Examples of hardware evidence could include serial output, timing measurements,
logic-analyser traces, or oscilloscope observations. The exact oracle depends on
the benchmark task.
