from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Iterable

import faiss

from processing.embedding_models import DEFAULT_MODEL_ALIAS, EMBEDDING_MODELS
from project_paths import METADATA_DB_PATH, faiss_index_path
from utils.db import initialize_metadata_db, make_index_id

DEFAULT_DB_PATH = METADATA_DB_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect the SQLite metadata database for chunking and retrieval debugging."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to the metadata SQLite database. Defaults to {DEFAULT_DB_PATH}.",
    )
    parser.add_argument(
        "--model",
        type=str.lower,
        choices=list(EMBEDDING_MODELS),
        default=DEFAULT_MODEL_ALIAS,
        help=f"Model used by index-integrity. Defaults to {DEFAULT_MODEL_ALIAS}.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("stats", help="Show overall chunk and paragraph statistics.")
    subparsers.add_parser("documents", help="Show per-document chunk and paragraph counts.")
    subparsers.add_parser(
        "index-status",
        help="Show the latest index build and current indexed chunk mapping counts.",
    )
    subparsers.add_parser(
        "index-integrity",
        help="Check whether chunk rows, indexed chunk mappings, and FAISS vectors agree.",
    )

    expansion_parser = subparsers.add_parser(
        "largest-expansions",
        help="Show chunks where the stored paragraph is much larger than the indexed chunk.",
    )
    expansion_parser.add_argument("--limit", type=int, default=10)

    page_parser = subparsers.add_parser(
        "page-chunks",
        help="Show indexed chunks for a specific file and page.",
    )
    page_parser.add_argument("--path-contains", required=True, help="Substring to match source_path.")
    page_parser.add_argument("--page", type=int, required=True)
    page_parser.add_argument("--limit", type=int, default=20)

    sql_parser = subparsers.add_parser(
        "sql",
        help="Run a custom read-only SQL query for debugging.",
    )
    sql_parser.add_argument("query", help="SQL query to execute.")

    return parser.parse_args()


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def print_rows(rows: Iterable[sqlite3.Row]) -> None:
    found_any = False
    for row in rows:
        found_any = True
        print(dict(row))
    if not found_any:
        print("No rows found.")


def ensure_safe_sql(query: str) -> None:
    normalized = " ".join(query.strip().lower().split())
    if not normalized.startswith("select"):
        raise SystemExit("Only SELECT queries are allowed.")


def command_stats(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        """
        SELECT
            COUNT(*) AS total_chunks,
            COUNT(DISTINCT source_path || '::' || COALESCE(CAST(page_number AS TEXT), '') || '::' || COALESCE(CAST(paragraph_index AS TEXT), '')) AS total_paragraphs,
            SUM(CASE WHEN paragraph_text = chunk_text THEN 1 ELSE 0 END) AS identical_rows,
            AVG(LENGTH(chunk_text)) AS avg_chunk_len,
            AVG(LENGTH(paragraph_text)) AS avg_paragraph_len
        FROM chunks
        """
    ).fetchone()
    print(dict(row))


def command_documents(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT
            source_path,
            COUNT(*) AS chunks,
            COUNT(DISTINCT source_path || '::' || COALESCE(CAST(page_number AS TEXT), '') || '::' || COALESCE(CAST(paragraph_index AS TEXT), '')) AS paragraphs
        FROM chunks
        GROUP BY source_path
        ORDER BY chunks DESC
        """
    ).fetchall()
    print_rows(rows)


def command_index_status(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT
            indexes.index_id,
            indexes.model_alias,
            indexes.embedding_model,
            indexes.dimensions,
            indexes.built_at,
            indexes.chunk_count,
            COUNT(indexed_chunks.vector_id) AS mapped_vectors,
            indexes.index_path
        FROM indexes
        LEFT JOIN indexed_chunks
            ON indexed_chunks.index_id = indexes.index_id
        GROUP BY indexes.index_id, indexes.model_alias, indexes.embedding_model,
                 indexes.dimensions, indexes.built_at, indexes.chunk_count,
                 indexes.index_path
        ORDER BY indexes.built_at DESC
        """
    ).fetchall()
    print_rows(rows)


def command_index_integrity(
    connection: sqlite3.Connection, model_alias: str, index_path: Path
) -> None:
    index_id = make_index_id(model_alias)
    counts = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM chunks) AS chunk_count,
            (SELECT COUNT(*) FROM indexed_chunks WHERE index_id = ?) AS indexed_chunk_count,
            (SELECT COALESCE(MAX(vector_id), -1) FROM indexed_chunks WHERE index_id = ?) AS max_vector_id
        """,
        (index_id, index_id),
    ).fetchone()

    faiss_vector_count = 0
    if index_path.exists():
        index = faiss.read_index(str(index_path))
        faiss_vector_count = int(index.ntotal)

    chunk_count = int(counts["chunk_count"])
    indexed_chunk_count = int(counts["indexed_chunk_count"])
    max_vector_id = int(counts["max_vector_id"])
    expected_next_vector_id = max_vector_id + 1 if indexed_chunk_count else 0
    counts_match = chunk_count == indexed_chunk_count == faiss_vector_count

    print(
        {
            "chunk_count": chunk_count,
            "model_alias": model_alias,
            "index_id": index_id,
            "indexed_chunk_count": indexed_chunk_count,
            "faiss_vector_count": faiss_vector_count,
            "max_vector_id": max_vector_id,
            "next_vector_id_if_appended": expected_next_vector_id,
            "counts_match": counts_match,
        }
    )

    if counts_match:
        print("Integrity check passed.")
        return

    print("Integrity check failed.")


def command_largest_expansions(connection: sqlite3.Connection, limit: int) -> None:
    rows = connection.execute(
        """
        SELECT
            source_path,
            page_number,
            paragraph_index,
            LENGTH(chunk_text) AS chunk_len,
            LENGTH(paragraph_text) AS para_len,
            REPLACE(SUBSTR(chunk_text, 1, 260), CHAR(10), ' | ') AS chunk_preview,
            REPLACE(SUBSTR(paragraph_text, 1, 420), CHAR(10), ' | ') AS para_preview
        FROM chunks
        ORDER BY (LENGTH(paragraph_text) - LENGTH(chunk_text)) DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    print_rows(rows)


def command_page_chunks(
    connection: sqlite3.Connection,
    path_contains: str,
    page: int,
    limit: int,
) -> None:
    rows = connection.execute(
        """
        SELECT
            page_number,
            paragraph_index,
            REPLACE(SUBSTR(chunk_text, 1, 200), CHAR(10), ' | ') AS chunk_preview
        FROM chunks
        WHERE source_path LIKE ?
          AND page_number = ?
        LIMIT ?
        """,
        (f"%{path_contains}%", page, limit),
    ).fetchall()
    print_rows(rows)


def command_sql(connection: sqlite3.Connection, query: str) -> None:
    ensure_safe_sql(query)
    rows = connection.execute(query).fetchall()
    print_rows(rows)


def main() -> None:
    args = parse_args()
    initialize_metadata_db(args.db)
    connection = connect(args.db)
    try:
        if args.command == "stats":
            command_stats(connection)
        elif args.command == "documents":
            command_documents(connection)
        elif args.command == "index-status":
            command_index_status(connection)
        elif args.command == "index-integrity":
            command_index_integrity(connection, args.model, faiss_index_path(args.model))
        elif args.command == "largest-expansions":
            command_largest_expansions(connection, args.limit)
        elif args.command == "page-chunks":
            command_page_chunks(connection, args.path_contains, args.page, args.limit)
        elif args.command == "sql":
            command_sql(connection, args.query)
        else:
            raise SystemExit(f"Unsupported command: {args.command}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
