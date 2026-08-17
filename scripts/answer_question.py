from __future__ import annotations

import argparse
import sys
from time import perf_counter

import faiss

from generation.ollama_provider import DEFAULT_OLLAMA_CHAT_URL, OllamaProvider
from generation.prompt_builder import (
    REFUSAL_TEXT,
    build_grounded_messages,
    referenced_source_labels,
    sources_from_retrieval,
)
from processing.embedder import TextEmbedder
from processing.embedding_models import EMBEDDING_MODELS, get_embedding_model
from project_paths import METADATA_DB_PATH, faiss_index_path
from search_index import ensure_search_inputs, search_query
from utils.db import initialize_metadata_db, make_index_id


DEFAULT_EMBEDDING_MODEL = "arctic"
DEFAULT_GENERATION_MODEL = "rageval-qwen"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Answer one question using local dense retrieval and Ollama."
    )
    parser.add_argument("question", help="Natural-language question to answer.")
    parser.add_argument(
        "--embedding",
        choices=list(EMBEDDING_MODELS),
        default=DEFAULT_EMBEDDING_MODEL,
        help=f"Retrieval embedding index. Defaults to {DEFAULT_EMBEDDING_MODEL}.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_GENERATION_MODEL,
        help=f"Ollama generation model. Defaults to {DEFAULT_GENERATION_MODEL}.",
    )
    parser.add_argument("--top-k", type=int, default=3, help="Evidence excerpts to supply.")
    parser.add_argument("--url", default=DEFAULT_OLLAMA_CHAT_URL, help="Ollama chat API URL.")
    parser.add_argument(
        "--no-stream", action="store_true", help="Wait for the complete answer before printing."
    )
    parser.add_argument(
        "--show-context", action="store_true", help="Print retrieved excerpts before generation."
    )
    return parser.parse_args()


def print_usage(result, retrieval_seconds: float) -> None:
    usage = result.usage
    print("\nMetrics:")
    print(f"  Retrieval:          {retrieval_seconds:.3f} s")
    if result.first_token_seconds is not None:
        print(f"  Time to first token:{result.first_token_seconds:9.3f} s")
    print(f"  Generation request:{result.wall_seconds:9.3f} s")
    print(f"  Prompt tokens:      {usage.prompt_tokens:9d}")
    print(f"  Output tokens:      {usage.output_tokens:9d}")
    print(f"  Total tokens:       {usage.total_tokens:9d}")
    print(f"  Generation speed:  {usage.output_tokens_per_second:9.2f} tokens/s")


def main() -> int:
    args = parse_args()
    if args.top_k < 1:
        print("Error: --top-k must be at least 1.", file=sys.stderr)
        return 2

    ensure_search_inputs(args.embedding)
    initialize_metadata_db(METADATA_DB_PATH)

    print(f"Loading {args.embedding} retrieval index...")
    retrieval_started_at = perf_counter()
    index = faiss.read_index(str(faiss_index_path(args.embedding)))
    embedder = TextEmbedder(get_embedding_model(args.embedding))
    index_id = make_index_id(args.embedding)
    results = search_query(
        args.question, index, embedder, index_id, top_k=args.top_k
    )
    retrieval_seconds = perf_counter() - retrieval_started_at
    sources = sources_from_retrieval(results)
    print(f"Retrieved {len(sources)} source excerpts in {retrieval_seconds:.3f} s.")

    if args.show_context:
        for source in sources:
            print(f"\n[{source.label}] {source.display_location}")
            print(source.text)

    messages = build_grounded_messages(args.question, sources)
    provider = OllamaProvider(args.model, url=args.url)
    stream = not args.no_stream

    print(f"\nAnswer from {args.model}:")
    try:
        result = provider.chat(
            messages,
            stream=stream,
            on_token=lambda token: print(token, end="", flush=True),
        )
    except RuntimeError as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 1

    if stream:
        print()
    else:
        print(result.content)

    source_lookup = {source.label: source for source in sources}
    cited_labels = referenced_source_labels(result.content)
    valid_citations = [source_lookup[label] for label in cited_labels if label in source_lookup]
    invalid_citations = [label for label in cited_labels if label not in source_lookup]

    if valid_citations:
        print("\nCited sources:")
        for source in valid_citations:
            print(f"  [{source.label}] {source.display_location}")
    if invalid_citations:
        print(f"\nWarning: unknown citation labels: {', '.join(invalid_citations)}")
    if result.content != REFUSAL_TEXT and not cited_labels:
        print("\nWarning: the answer made a claim without a source label.")

    print_usage(result, retrieval_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
