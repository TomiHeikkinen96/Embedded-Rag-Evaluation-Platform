from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

SCHEMA_VERSION = 2
DEFAULT_CHUNKER_ALIAS = "custom"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_index_id(model_alias: str, chunker_alias: str = DEFAULT_CHUNKER_ALIAS) -> str:
    return f"{chunker_alias}:{model_alias}"


@contextmanager
def sqlite_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_metadata_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite_connection(db_path) as connection:
        existing_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        current_version = int(
            connection.execute("PRAGMA user_version").fetchone()[0]
        )
        has_metadata_schema = bool(
            existing_tables & {"chunks", "indexes", "indexed_chunks"}
        )
        if has_metadata_schema and current_version != SCHEMA_VERSION:
            raise RuntimeError(
                "Unsupported metadata schema version "
                f"{current_version}; expected {SCHEMA_VERSION}. "
                "Run ./ingest_data.sh --clean to recreate generated storage."
            )
        _create_metadata_schema(connection)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _create_metadata_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            title TEXT,
            chunk_text TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            page_number INTEGER,
            paragraph_index INTEGER,
            paragraph_text TEXT,
            section_heading TEXT,
            ingestion_timestamp TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS indexes (
            index_id TEXT PRIMARY KEY,
            chunker_alias TEXT NOT NULL,
            model_alias TEXT NOT NULL,
            embedding_model TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            built_at TEXT NOT NULL,
            chunk_count INTEGER NOT NULL,
            index_path TEXT NOT NULL,
            UNIQUE(chunker_alias, model_alias)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS indexed_chunks (
            index_id TEXT NOT NULL,
            vector_id INTEGER NOT NULL,
            chunk_id TEXT NOT NULL,
            indexed_at TEXT NOT NULL,
            PRIMARY KEY(index_id, vector_id),
            UNIQUE(index_id, chunk_id),
            FOREIGN KEY (index_id) REFERENCES indexes(index_id) ON DELETE CASCADE,
            FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_source_path ON chunks(source_path)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_indexed_chunks_chunk_id ON indexed_chunks(chunk_id)"
    )


def initialize_file_tracking_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                file_path TEXT PRIMARY KEY,
                file_hash TEXT NOT NULL,
                last_processed TEXT NOT NULL,
                last_seen TEXT,
                is_present INTEGER NOT NULL DEFAULT 1,
                deleted_at TEXT
            )
            """
        )


def get_file_record(db_path: Path, file_path: str) -> Optional[sqlite3.Row]:
    with sqlite_connection(db_path) as connection:
        return connection.execute(
            """
            SELECT file_path, file_hash, last_processed, last_seen, is_present, deleted_at
            FROM files WHERE file_path = ?
            """,
            (file_path,),
        ).fetchone()


def fetch_all_file_records(db_path: Path) -> list[sqlite3.Row]:
    with sqlite_connection(db_path) as connection:
        return connection.execute(
            """
            SELECT file_path, file_hash, last_processed, last_seen, is_present, deleted_at
            FROM files ORDER BY file_path
            """
        ).fetchall()


def record_file_seen(db_path: Path, file_path: str, file_hash: str) -> None:
    timestamp = utc_now_iso()
    with sqlite_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO files(file_path, file_hash, last_processed, last_seen, is_present, deleted_at)
            VALUES (?, ?, ?, ?, 1, NULL)
            ON CONFLICT(file_path) DO UPDATE SET
                file_hash = excluded.file_hash,
                last_seen = excluded.last_seen,
                is_present = 1,
                deleted_at = NULL
            """,
            (file_path, file_hash, timestamp, timestamp),
        )


def upsert_file_record(db_path: Path, file_path: str, file_hash: str) -> None:
    timestamp = utc_now_iso()
    with sqlite_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO files(file_path, file_hash, last_processed, last_seen, is_present, deleted_at)
            VALUES (?, ?, ?, ?, 1, NULL)
            ON CONFLICT(file_path) DO UPDATE SET
                file_hash = excluded.file_hash,
                last_processed = excluded.last_processed,
                last_seen = excluded.last_seen,
                is_present = 1,
                deleted_at = NULL
            """,
            (file_path, file_hash, timestamp, timestamp),
        )


def mark_file_deleted(db_path: Path, file_path: str) -> None:
    timestamp = utc_now_iso()
    with sqlite_connection(db_path) as connection:
        connection.execute(
            """
            UPDATE files
            SET is_present = 0, deleted_at = ?, last_seen = ?
            WHERE file_path = ?
            """,
            (timestamp, timestamp, file_path),
        )


def insert_chunk_rows(db_path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with sqlite_connection(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO chunks(
                chunk_id, document_id, source_path, file_type, title, chunk_text,
                chunk_index, page_number, paragraph_index, paragraph_text,
                section_heading, ingestion_timestamp
            )
            VALUES (
                :chunk_id, :document_id, :source_path, :file_type, :title, :chunk_text,
                :chunk_index, :page_number, :paragraph_index, :paragraph_text,
                :section_heading, :ingestion_timestamp
            )
            """,
            rows,
        )


def fetch_all_chunks(db_path: Path) -> list[sqlite3.Row]:
    with sqlite_connection(db_path) as connection:
        return connection.execute(
            "SELECT * FROM chunks ORDER BY source_path, page_number, chunk_index, chunk_id"
        ).fetchall()


def delete_document_chunks(db_path: Path, document_id: str) -> None:
    with sqlite_connection(db_path) as connection:
        connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))


def clear_all_index_metadata(db_path: Path) -> None:
    with sqlite_connection(db_path) as connection:
        connection.execute("DELETE FROM indexes")


def count_chunks(db_path: Path) -> int:
    with sqlite_connection(db_path) as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()
        return int(row["count"])


def count_index_entries(db_path: Path, index_id: str) -> int:
    with sqlite_connection(db_path) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM indexed_chunks WHERE index_id = ?",
            (index_id,),
        ).fetchone()
        return int(row["count"])


def replace_index(
    db_path: Path,
    *,
    index_id: str,
    chunker_alias: str,
    model_alias: str,
    embedding_model: str,
    dimensions: int,
    chunk_count: int,
    index_path: str,
    chunk_ids: list[str],
) -> None:
    timestamp = utc_now_iso()
    with sqlite_connection(db_path) as connection:
        connection.execute("DELETE FROM indexes WHERE index_id = ?", (index_id,))
        connection.execute(
            """
            INSERT INTO indexes(
                index_id, chunker_alias, model_alias, embedding_model,
                dimensions, built_at, chunk_count, index_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                index_id, chunker_alias, model_alias, embedding_model,
                dimensions, timestamp, chunk_count, index_path,
            ),
        )
        connection.executemany(
            """
            INSERT INTO indexed_chunks(index_id, vector_id, chunk_id, indexed_at)
            VALUES (?, ?, ?, ?)
            """,
            [
                (index_id, vector_id, chunk_id, timestamp)
                for vector_id, chunk_id in enumerate(chunk_ids)
            ],
        )


def get_index_record(db_path: Path, index_id: str) -> Optional[sqlite3.Row]:
    with sqlite_connection(db_path) as connection:
        return connection.execute(
            "SELECT * FROM indexes WHERE index_id = ?", (index_id,)
        ).fetchone()


def fetch_index_records(db_path: Path) -> list[sqlite3.Row]:
    with sqlite_connection(db_path) as connection:
        return connection.execute(
            "SELECT * FROM indexes ORDER BY chunker_alias, model_alias"
        ).fetchall()


def fetch_indexed_chunks(db_path: Path, index_id: str) -> list[sqlite3.Row]:
    with sqlite_connection(db_path) as connection:
        return connection.execute(
            """
            SELECT
                indexed_chunks.vector_id, chunks.chunk_id, chunks.source_path,
                chunks.page_number, chunks.paragraph_index, chunks.chunk_text,
                chunks.paragraph_text, chunks.title, chunks.section_heading
            FROM indexed_chunks
            JOIN chunks ON chunks.chunk_id = indexed_chunks.chunk_id
            WHERE indexed_chunks.index_id = ?
            ORDER BY indexed_chunks.vector_id
            """,
            (index_id,),
        ).fetchall()


def fetch_chunks_by_vector_ids(
    db_path: Path, index_id: str, vector_ids: list[int]
) -> list[sqlite3.Row]:
    if not vector_ids:
        return []
    placeholders = ",".join("?" for _ in vector_ids)
    order_by = "CASE indexed_chunks.vector_id " + " ".join(
        f"WHEN ? THEN {position}" for position, _ in enumerate(vector_ids)
    ) + " END"
    parameters = [index_id, *vector_ids, *vector_ids]
    with sqlite_connection(db_path) as connection:
        return connection.execute(
            f"""
            SELECT
                indexed_chunks.vector_id, indexed_chunks.index_id,
                chunks.chunk_id, chunks.source_path, chunks.page_number,
                chunks.paragraph_index, chunks.chunk_text, chunks.paragraph_text,
                chunks.title, chunks.section_heading
            FROM indexed_chunks
            JOIN chunks ON chunks.chunk_id = indexed_chunks.chunk_id
            WHERE indexed_chunks.index_id = ?
              AND indexed_chunks.vector_id IN ({placeholders})
            ORDER BY {order_by}
            """,
            parameters,
        ).fetchall()
