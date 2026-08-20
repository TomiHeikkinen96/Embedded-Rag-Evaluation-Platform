# Example AI-Assisted Development Discussion

This is a simulated but repository-grounded example of how AI assistance is
used during development of RAGeval. It records an **ask first, implement
second** discussion: the developer proposes a feature and retains control of
scope and architecture, while the AI inspects the existing code, identifies
coupling and risks, and turns the discussion into an implementation boundary.

The prompts are preserved as written, apart from Markdown formatting. The AI
responses are condensed for readability. No retrieval feature was implemented
as part of creating this example.

## Turn 1 — inspect the requested experiment

### Developer prompt

> I want to add new feature to the retrieval evaluation. Currently we have the
> three embedding models and our custom-made chunking method. I want to add
> simpler evaluation framework, so we can test what happens to the retrieval
> quality if we are changing from our current solution to something like 500
> characters flat chunking, does it improve, decrease or no effect on retrieval
> quality. We currently have 3 different embeddings models and their vector
> databases, this would add 3 more FAISS dbs. Could you check how big of a
> change this would be, then let's spitball about the architectural choices. I
> think it should be fairly modular, so can you check how much it would add to
> add new chunking method?
>
> Especially when considering there is the `./local_ingest_data.sh`, I worry
> that there might be some drift there. Does using parameter `--clean` only
> destroy that specific model data, or does it delete all the data? If we also
> use model parameter.

### AI response

This is a moderate change, not a rewrite. The fixed-width chunker itself would
be small; most of the work comes from making chunking a selectable experimental
axis throughout ingestion, storage, search, and evaluation.

This would create six FAISS indexes—three embedding models multiplied by two
chunkers—not six SQLite databases. I would keep one inspectable metadata layer
and give every index an explicit `(chunker, model)` identity:

```text
storage/indexes/custom/mini.faiss
storage/indexes/custom/bge.faiss
storage/indexes/custom/arctic.faiss
storage/indexes/raw500/mini.faiss
storage/indexes/raw500/bge.faiss
storage/indexes/raw500/arctic.faiss
```

The existing design is partly ready for this: index IDs and FAISS paths already
accept a chunker alias. The incomplete part is that ingestion and search still
use the custom chunker implicitly, and SQLite currently represents one shared
chunk set. Adding the class is therefore small, while supporting six isolated,
comparable conditions is a moderate cross-cutting change.

The likely work is:

- add a `Raw500Chunker` behind the existing chunker interface
- introduce a strict chunker registry and `--chunker` selector
- attach chunker identity to stored chunks and index construction
- pass chunker selection through search, benchmark, inspection, and
  visualization commands
- test chunk boundaries, condition isolation, cleanup, and evidence matching
- keep the retrieval design and command documentation aligned

There is a real cleanup surprise. `local_ingest_data.sh` translates `--clean`
to `--force-rebuild`. The Python ingestion command then deletes both generated
SQLite databases and every FAISS file before rebuilding only the selected
model. Therefore:

```bash
./local_ingest_data.sh --model mini --clean
```

deletes all generated indexes and metadata, then rebuilds only MiniLM. BGE and
Arctic are left absent. A source-document change has a related issue: it
invalidates all model indexes, but only selected models are rebuilt.

For a fair first comparison, `raw500` should be defined before implementation:

- sequential windows of at most 500 characters
- no overlap
- no crossing of physical PDF page boundaries, because benchmark evidence is
  page-labelled
- the same source corpus, embedding models, candidate pool, reranker, labels,
  and metrics as the custom chunker
- reported chunk counts, size distribution, ingestion time, index size, and
  retrieval metrics

The architectural choice is whether alternate chunkers should immediately
inherit the full incremental-ingestion lifecycle, or whether evaluation builds
should be deliberately disposable and clean-built. The latter is simpler and
makes the first experiment easier to reproduce.

## Turn 2 — developer narrows the architecture

### Developer prompt

> For now the clean is fine, I am thinking we should add that to the
> documentation like I'd probably want model specific clean, it would require a
> given model to work or it would give a fault. Then we could use
> `--force-clean` for the full clean, but let's just document it for further
> development now and proceed with the 500 characters implementation now.
>
> Original scope was to have more of a generic tool that would be able to
> ingest data cleanly and nicely, we used the MD5 hashing for the exact reason
> that we could be able to later add docs, and it wouldn't be costly and it
> would also be a nice "scaling" exercise and demonstration. But I feel like
> there is a scope creep if we try to maintain a database tool that would solve
> all that, so I am thinking we should maybe separate databases and commands a
> bit, like now we have massive database tool for evaluation - maybe we could
> turn it that the evaluation is rechunked every time, but then add like another
> pipeline that would then have the hashed metadata & otherwise to ensure we can
> keep tweaking and trying out the dataset, as part of the project.
>
> Could you document the planning and add it todo?

### AI response

That separation is a good scope boundary. One small factual correction before
recording it: the repository currently hashes files with SHA-256 rather than
MD5. The architectural intent is the same—unchanged documents can be detected
without repeatedly parsing and embedding them.

I would separate **artifact lifecycle and commands**, but continue sharing the
loader, chunkers, embedders, FAISS mapping, and benchmark primitives. Creating
two independent implementations would introduce the drift we are trying to
avoid.

The two workflows would be:

1. **Retrieval evaluation build**

   Treat generated chunks and indexes as disposable experiment artifacts.
   Rechunk the locked corpus for each declared chunker configuration, rebuild
   the requested model matrix, and save enough configuration and metrics to
   reproduce the comparison. This path favours determinism and fair comparisons
   over incremental updates.

2. **Incremental ingestion demonstration**

   Retain SHA-256 file tracking, changed/deleted-document detection, and a
   selected active chunking/index configuration. This path demonstrates how a
   longer-lived corpus could avoid unnecessary reprocessing. It can evolve
   separately without forcing every experimental chunker to support production-
   style migration and invalidation semantics.

The storage namespaces and root commands should make that distinction visible.
Their exact names can be chosen during implementation, but an evaluation command
should not silently mutate the active incremental index, and an incremental
ingestion command should not be responsible for materializing the entire
evaluation matrix.

The cleanup redesign belongs in future work rather than in the raw-500 change:

- `--clean` would be condition-specific and require explicit selectors such as
  `--model`; missing required selectors would fail without deleting anything
- `--force-clean` would remain the deliberately global cleanup operation
- help and confirmation output would enumerate the exact artifacts affected
- until that redesign is implemented, documentation must continue to state
  that the current `--clean` behaviour is global

For the first implementation slice, I would therefore add `raw500` as a
clean-built evaluation condition, preserve physical page metadata for benchmark
matching, and avoid expanding the incremental database lifecycle at the same
time. That changes one experimental dimension while keeping the scope
inspectable.

The planning is now captured in the documentation and `todo.md`. Great, I am
starting to implement the feature now...

## What this example demonstrates

- The developer supplied the problem, scaling intent, and acceptable scope.
- The AI inspected current behaviour before proposing changes.
- The discussion found a destructive-cleanup edge case before implementation.
- The developer rejected unnecessary lifecycle complexity for the experiment.
- The AI corrected a small factual mismatch and preserved the underlying idea.
- Architecture and deferred work were recorded before implementation began.

In a real task, the next step would be a scoped implementation followed by
tests, benchmark validation, diff review, and acceptance by the developer. This
example intentionally stops before that work.
