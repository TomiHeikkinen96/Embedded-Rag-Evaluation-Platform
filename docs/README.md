# Documentation

The root README is the public project overview. These notes contain the details
needed to understand, run, and extend the experiment.

## Current system

- [Architecture](architecture.md) — current components, data flow, and boundaries
- [Local workflow](local-workflow.md) — Docker setup and supported commands
- [Ingestion](ingestion.md) — discovery, hashing, incremental updates, and clean rebuilds
- [Retrieval pipeline](retrieval-pipeline.md) — indexing, search, reranking, and metadata mapping
- [Visualization](visualization.md) — what the 3D explorer shows and what it cannot prove

## Evaluation and direction

- [Evaluation](evaluation.md) — retrieval and generation metrics, ground truth, and failure attribution
- [Local model](local-model.md) — Ollama setup, Modelfile, and generation conditions
- [Roadmap](roadmap.md) — the four project phases and their completion criteria
- [Retrieval evaluation plan](retrieval-evaluation-plan.md) — detailed proposed 3 × 3 experiment matrix and refactor sequence
- [Next checkpoint](../NEXT_STEPS.md) — the immediate implementation order
- [Working task list](../todo.md) — concise engineering work log
