from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import faiss
import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from processing.embedder import TextEmbedder
from project_paths import BENCHMARK_QUERIES_PATH, VISUALIZATION_DIR
from search_index import EMBEDDING_MODEL_NAME, INDEX_PATH, METADATA_DB_PATH


DEFAULT_QUERY_FILE = BENCHMARK_QUERIES_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create browser-ready PCA coordinates from the active FAISS index."
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


def load_indexed_chunks() -> list[sqlite3.Row]:
    connection = sqlite3.connect(METADATA_DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(
            """
            SELECT ic.vector_id, c.page_number, c.chunk_text
            FROM indexed_chunks AS ic
            JOIN chunks AS c ON c.chunk_id = ic.chunk_id
            ORDER BY ic.vector_id
            """
        ).fetchall()
    finally:
        connection.close()


def normalized_pca_3d(vectors: np.ndarray) -> np.ndarray:
    centered = vectors - vectors.mean(axis=0, keepdims=True)
    _, _, axes = np.linalg.svd(centered, full_matrices=False)
    coordinates = centered @ axes[:3].T
    scale = np.max(np.abs(coordinates), axis=0)
    return coordinates / np.where(scale == 0, 1, scale)


def generate_payload(queries: list[str]) -> dict:
    if not INDEX_PATH.exists() or not METADATA_DB_PATH.exists():
        raise SystemExit("The active FAISS index and metadata database are required.")

    index = faiss.read_index(str(INDEX_PATH))
    rows = load_indexed_chunks()
    if not rows:
        raise SystemExit("The active index contains no mapped chunks.")

    chunk_vectors = np.stack(
        [index.reconstruct(int(row["vector_id"])) for row in rows]
    )
    query_vectors = TextEmbedder(EMBEDDING_MODEL_NAME).embed_texts(queries)
    coordinates = normalized_pca_3d(np.vstack([chunk_vectors, query_vectors]))
    similarities = chunk_vectors @ query_vectors.T

    return {
        "projection": "PCA",
        "original_dimensions": int(chunk_vectors.shape[1]),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "queries": queries,
        "points": [
            {
                "id": int(row["vector_id"]),
                "page": row["page_number"],
                "text": " ".join(row["chunk_text"].split())[:180],
                "xyz": [round(float(value), 4) for value in coordinates[index_number]],
                "similarities": [
                    round(float(value), 4) for value in similarities[index_number]
                ],
            }
            for index_number, row in enumerate(rows)
        ],
        "query_points": [
            [round(float(value), 4) for value in coordinates[len(rows) + index_number]]
            for index_number in range(len(queries))
        ],
    }


def main() -> None:
    args = parse_args()
    payload = generate_payload(load_queries(args.queries))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, separators=(",", ":")),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(payload['points'])} chunks and "
        f"{len(payload['queries'])} queries to {args.output}"
    )


if __name__ == "__main__":
    main()
