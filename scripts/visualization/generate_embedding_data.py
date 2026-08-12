from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import faiss
import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from processing.embedder import TextEmbedder
from processing.embedding_models import EMBEDDING_MODELS, get_embedding_model, resolve_model_aliases
from project_paths import (
    BENCHMARK_QUERIES_PATH,
    METADATA_DB_PATH,
    VISUALIZATION_DIR,
    faiss_index_path,
)
from utils.db import fetch_indexed_chunks, initialize_metadata_db, make_index_id

DEFAULT_QUERY_FILE = BENCHMARK_QUERIES_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create browser-ready PCA coordinates for model comparisons."
    )
    parser.add_argument(
        "--model",
        type=str.lower,
        choices=[*EMBEDDING_MODELS, "all"],
        default="all",
        help="Models to include. Defaults to all registered models.",
    )
    parser.add_argument(
        "--queries",
        type=Path,
        default=DEFAULT_QUERY_FILE,
        help="Text file containing one benchmark query per line.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=VISUALIZATION_DIR / "embedding-data.json",
        help="Destination JSON file used by visualization/index.html.",
    )
    return parser.parse_args()


def load_queries(path: Path) -> list[str]:
    queries = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not queries:
        raise SystemExit(f"No benchmark queries found in {path}")
    return queries


def pca_projection_3d(
    chunk_vectors: np.ndarray, query_vectors: np.ndarray
) -> tuple[np.ndarray, np.ndarray, list[float]]:
    center = chunk_vectors.mean(axis=0, keepdims=True)
    centered_chunks = chunk_vectors - center
    _, singular_values, axes = np.linalg.svd(centered_chunks, full_matrices=False)
    component_axes = axes[:3]
    chunk_coordinates = centered_chunks @ component_axes.T
    query_coordinates = (query_vectors - center) @ component_axes.T

    total_variance = float(np.sum(singular_values**2))
    explained_variance = (
        (singular_values[:3] ** 2 / total_variance).tolist()
        if total_variance > 0
        else [0.0, 0.0, 0.0]
    )
    scale = np.max(np.abs(chunk_coordinates), axis=0)
    safe_scale = np.where(scale == 0, 1, scale)
    return (
        chunk_coordinates / safe_scale,
        query_coordinates / safe_scale,
        [round(float(value), 6) for value in explained_variance],
    )


def generate_model_payload(model_alias: str, queries: list[str]) -> dict:
    config = get_embedding_model(model_alias)
    index_path = faiss_index_path(model_alias)
    if not index_path.exists():
        raise SystemExit(
            f"Missing {model_alias} index at {index_path}. "
            f"Run ./ingest_data.sh --model {model_alias} first."
        )

    index_id = make_index_id(model_alias)
    rows = fetch_indexed_chunks(METADATA_DB_PATH, index_id)
    if not rows:
        raise SystemExit(f"The {model_alias} index has no mapped chunks in SQLite.")
    index = faiss.read_index(str(index_path))
    if int(index.ntotal) != len(rows):
        raise SystemExit(
            f"The {model_alias} FAISS and SQLite counts disagree "
            f"({int(index.ntotal)} vs {len(rows)}). Rebuild that model index."
        )

    chunk_vectors = np.stack(
        [index.reconstruct(int(row["vector_id"])) for row in rows]
    )
    query_vectors = TextEmbedder(config).embed_texts(queries, input_type="query")
    chunk_coordinates, query_coordinates, explained_variance = pca_projection_3d(
        chunk_vectors, query_vectors
    )
    similarities = chunk_vectors @ query_vectors.T

    return {
        "alias": model_alias,
        "display_name": config.display_name,
        "model_id": config.model_id,
        "role": config.role,
        "original_dimensions": int(chunk_vectors.shape[1]),
        "explained_variance": explained_variance,
        "points": [
            {
                "id": int(row["vector_id"]),
                "page": row["page_number"],
                "text": " ".join(row["chunk_text"].split())[:180],
                "xyz": [round(float(value), 4) for value in chunk_coordinates[position]],
                "similarities": [
                    round(float(value), 4) for value in similarities[position]
                ],
            }
            for position, row in enumerate(rows)
        ],
        "query_points": [
            [round(float(value), 4) for value in query_coordinates[position]]
            for position in range(len(queries))
        ],
    }


def generate_payload(model_aliases: list[str], queries: list[str]) -> dict:
    if not METADATA_DB_PATH.exists():
        raise SystemExit(f"Metadata database not found at {METADATA_DB_PATH}")
    initialize_metadata_db(METADATA_DB_PATH)
    return {
        "projection": "PCA fitted independently on each model corpus",
        "queries": queries,
        "models": [
            generate_model_payload(model_alias, queries)
            for model_alias in model_aliases
        ],
    }


def main() -> None:
    args = parse_args()
    queries = load_queries(args.queries)
    payload = generate_payload(resolve_model_aliases(args.model), queries)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, separators=(",", ":")), encoding="utf-8"
    )
    model_names = ", ".join(model["alias"] for model in payload["models"])
    print(
        f"Wrote {len(payload['models'])} models ({model_names}), "
        f"{len(payload['queries'])} queries, and "
        f"{len(payload['models'][0]['points'])} shared chunks to {args.output}"
    )


if __name__ == "__main__":
    main()
