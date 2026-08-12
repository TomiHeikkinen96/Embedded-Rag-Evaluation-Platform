from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingModelConfig:
    alias: str
    model_id: str
    display_name: str
    role: str
    query_prefix: str = ""
    document_prefix: str = ""
    trust_remote_code: bool = False


EMBEDDING_MODELS = {
    "mini": EmbeddingModelConfig(
        alias="mini",
        model_id="sentence-transformers/all-MiniLM-L6-v2",
        display_name="MiniLM L6 v2",
        role="Fast general baseline",
    ),
    "bge": EmbeddingModelConfig(
        alias="bge",
        model_id="BAAI/bge-base-en-v1.5",
        display_name="BGE base v1.5",
        role="Medium retrieval model",
        query_prefix="Represent this sentence for searching relevant passages: ",
    ),
    "technical": EmbeddingModelConfig(
        alias="technical",
        model_id="jinaai/jina-embeddings-v2-base-code",
        display_name="Jina embeddings v2 code",
        role="Technical and code-biased candidate",
        trust_remote_code=True,
    ),
}

DEFAULT_MODEL_ALIAS = "mini"


def get_embedding_model(alias: str) -> EmbeddingModelConfig:
    try:
        return EMBEDDING_MODELS[alias]
    except KeyError as exc:
        choices = ", ".join(EMBEDDING_MODELS)
        raise ValueError(f"Unknown embedding model '{alias}'. Choose one of: {choices}") from exc


def resolve_model_aliases(selection: str) -> list[str]:
    if selection == "all":
        return list(EMBEDDING_MODELS)
    get_embedding_model(selection)
    return [selection]
