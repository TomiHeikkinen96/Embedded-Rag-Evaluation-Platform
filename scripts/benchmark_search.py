from __future__ import annotations

import argparse
from pathlib import Path

import faiss

from processing.embedder import TextEmbedder
from processing.embedding_models import DEFAULT_MODEL_ALIAS, EMBEDDING_MODELS, get_embedding_model
from project_paths import BENCHMARK_QUERIES_PATH, PROJECT_ROOT
from search_index import (
    METADATA_DB_PATH,
    ensure_search_inputs,
    preview_text,
    search_query,
)
from project_paths import faiss_index_path
from utils.db import initialize_metadata_db, make_index_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a standardized batch of search queries against the local index."
    )
    parser.add_argument(
        "--model",
        type=str.lower,
        choices=list(EMBEDDING_MODELS),
        default=DEFAULT_MODEL_ALIAS,
        help=f"Embedding model index to evaluate. Defaults to {DEFAULT_MODEL_ALIAS}.",
    )
    parser.add_argument(
        "queries",
        nargs="*",
        help="Query strings to evaluate. If omitted, queries are loaded from --file.",
    )
    parser.add_argument(
        "--file",
        default=str(BENCHMARK_QUERIES_PATH),
        help="Path to a text file containing one query per line.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of results to print for each query.",
    )
    return parser.parse_args()


def load_queries(args: argparse.Namespace) -> list[str]:
    if args.queries:
        return args.queries

    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path

    if not file_path.exists():
        raise SystemExit(
            f"Benchmark query file not found: {file_path}\n"
            "Provide queries as arguments or create the file."
        )

    with open(file_path, "r", encoding="utf-8") as handle:
        return [
            line.strip()
            for line in handle
            if line.strip() and not line.lstrip().startswith("#")
        ]


def main() -> None:
    args = parse_args()
    queries = load_queries(args)
    if not queries:
        raise SystemExit("No benchmark queries provided.")

    ensure_search_inputs(args.model)
    initialize_metadata_db(METADATA_DB_PATH)

    index = faiss.read_index(str(faiss_index_path(args.model)))
    embedder = TextEmbedder(get_embedding_model(args.model))
    index_id = make_index_id(args.model)

    for query_index, query in enumerate(queries):
        if query_index > 0:
            print("=" * 80)

        print(f"Query: {query}")
        print()
        results = search_query(query, index, embedder, index_id)
        if not results:
            print("No matches found.")
            print()
            continue

        for rank, result in enumerate(results[: args.top_k], start=1):
            row = result["row"]
            print(f"Rank: {rank}")
            print(f"Final Score: {result['rerank_score']:.2f}")
            print(f"Semantic Score: {result['semantic_score']:.2f}")
            print(f"Lexical Score: {result['lexical_score']:.2f}")
            print(f"Penalty: {result['penalty']:.2f}")
            print(f"File: {row['source_path']}")
            print(f"Page: {row['page_number']}")
            print("Chunk:")
            print(preview_text(row["chunk_text"], limit=220))
            print()


if __name__ == "__main__":
    main()
