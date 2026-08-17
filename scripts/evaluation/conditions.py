from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from evaluation.benchmark import GenerationCase
from generation.prompt_builder import (
    GroundedSource,
    build_closed_book_messages,
    build_grounded_messages,
    sources_from_retrieval,
)


@dataclass(frozen=True)
class PreparedCondition:
    messages: list[dict[str, str]]
    sources: list[GroundedSource]
    context_seconds: float
    retrieval_evidence_hit: bool | None


class ArcticRetriever:
    """Load the Arctic index once and reuse it across an evaluation run."""

    def __init__(self) -> None:
        import faiss

        from processing.embedder import TextEmbedder
        from processing.embedding_models import get_embedding_model
        from project_paths import METADATA_DB_PATH, faiss_index_path
        from search_index import ensure_search_inputs
        from utils.db import initialize_metadata_db, make_index_id

        self.model_alias = "arctic"
        ensure_search_inputs(self.model_alias)
        initialize_metadata_db(METADATA_DB_PATH)
        self.index = faiss.read_index(str(faiss_index_path(self.model_alias)))
        self.embedder = TextEmbedder(get_embedding_model(self.model_alias))
        self.index_id = make_index_id(self.model_alias)

    def retrieve(self, question: str, top_k: int) -> list[dict]:
        from search_index import search_query

        return search_query(
            question, self.index, self.embedder, self.index_id, top_k=top_k
        )


def _oracle_sources(case: GenerationCase) -> list[GroundedSource]:
    return [
        GroundedSource(
            label=f"S{position}",
            title=source["title"],
            source_path=source["source_path"],
            page_number=source.get("page_number"),
            text=source["text"],
            semantic_score=1.0,
            rerank_score=1.0,
        )
        for position, source in enumerate(case.oracle_sources, start=1)
    ]


def _retrieval_hit(case: GenerationCase, sources: list[GroundedSource]) -> bool:
    expected_locations = {
        (source["source_path"].split("/")[-1], source.get("page_number"))
        for source in case.oracle_sources
    }
    retrieved_locations = {
        (source.source_path.split("/")[-1], source.page_number) for source in sources
    }
    return bool(expected_locations & retrieved_locations)


def prepare_condition(
    condition: str,
    case: GenerationCase,
    *,
    top_k: int,
    retriever: ArcticRetriever | None,
) -> PreparedCondition:
    started_at = perf_counter()

    if condition == "closed_book":
        return PreparedCondition(
            messages=build_closed_book_messages(case.question),
            sources=[],
            context_seconds=perf_counter() - started_at,
            retrieval_evidence_hit=None,
        )

    if condition == "oracle":
        sources = _oracle_sources(case)
        return PreparedCondition(
            messages=build_grounded_messages(case.question, sources),
            sources=sources,
            context_seconds=perf_counter() - started_at,
            retrieval_evidence_hit=None,
        )

    if condition == "dense_rag:arctic":
        if retriever is None:
            raise RuntimeError("The Arctic retriever was not initialized.")
        sources = sources_from_retrieval(retriever.retrieve(case.question, top_k))
        return PreparedCondition(
            messages=build_grounded_messages(case.question, sources),
            sources=sources,
            context_seconds=perf_counter() - started_at,
            retrieval_evidence_hit=_retrieval_hit(case, sources)
            if case.oracle_sources
            else None,
        )

    raise ValueError(f"Unsupported condition: {condition}")
