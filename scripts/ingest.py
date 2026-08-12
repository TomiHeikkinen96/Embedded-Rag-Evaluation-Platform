from __future__ import annotations

import argparse
import sys
from time import perf_counter
from pathlib import Path
from uuid import uuid4

import numpy as np

try:
    import faiss
except ImportError as exc:
    raise ImportError(
        "FAISS is required for indexing. Install dependencies with "
        "`pip install -r requirements.txt`."
    ) from exc

from chunkers.pdf_chunker import PDFChunker
from processing.embedder import TextEmbedder
from processing.embedding_models import EMBEDDING_MODELS, get_embedding_model, resolve_model_aliases
from processing.pdf_loader import load_pdf_pages
from project_paths import (
    DATA_DIR,
    FILE_TRACKING_DB_PATH,
    INDEXES_DIR,
    METADATA_DB_PATH,
    STORAGE_DIR,
    faiss_index_path,
)
from utils.db import (
    DEFAULT_CHUNKER_ALIAS,
    clear_all_index_metadata,
    count_chunks,
    count_index_entries,
    delete_document_chunks,
    fetch_all_chunks,
    fetch_all_file_records,
    get_file_record,
    get_index_record,
    initialize_file_tracking_db,
    initialize_metadata_db,
    insert_chunk_rows,
    make_index_id,
    mark_file_deleted,
    record_file_seen,
    replace_index,
    upsert_file_record,
    utc_now_iso,
)
from utils.hashing import sha256_file

CHUNKERS = {".pdf": PDFChunker()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build model-specific FAISS indexes over the shared PDF chunks."
    )
    parser.add_argument(
        "--model",
        type=str.lower,
        choices=[*EMBEDDING_MODELS, "all"],
        default="all",
        help="Embedding model to build. Defaults to all registered models.",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="After confirmation, clear generated indexes and metadata before ingesting.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompts. Intended for explicit automation.",
    )
    return parser.parse_args()


def ensure_directories() -> None:
    if not DATA_DIR.exists():
        print(f"Error: data directory not found at {DATA_DIR}")
        sys.exit(1)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    INDEXES_DIR.mkdir(parents=True, exist_ok=True)


def discover_pdf_files() -> list[Path]:
    return sorted(
        path
        for path in DATA_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() == ".pdf"
    )


def generated_index_paths() -> list[Path]:
    return list(INDEXES_DIR.rglob("*.faiss")) if INDEXES_DIR.exists() else []


def clear_generated_indexes() -> None:
    for path in generated_index_paths():
        path.unlink()


def reset_storage() -> None:
    print("Clean rebuild requested. Clearing generated storage.")
    for database_path in (METADATA_DB_PATH, FILE_TRACKING_DB_PATH):
        database_path.unlink(missing_ok=True)
        Path(f"{database_path}-wal").unlink(missing_ok=True)
        Path(f"{database_path}-shm").unlink(missing_ok=True)
    clear_generated_indexes()


def detect_files_to_process(pdf_paths: list[Path]) -> tuple[list[dict], list[dict]]:
    process_queue: list[dict] = []
    seen_files: list[dict] = []
    for pdf_path in pdf_paths:
        file_hash = sha256_file(pdf_path)
        seen_files.append({"path": pdf_path, "hash": file_hash})
        record = get_file_record(FILE_TRACKING_DB_PATH, str(pdf_path))
        if record is None:
            status = "NEW"
        elif not record["is_present"]:
            status = "RESTORED"
        elif record["file_hash"] != file_hash:
            status = "CHANGED"
        else:
            continue
        process_queue.append({"path": pdf_path, "hash": file_hash, "status": status})
    return process_queue, seen_files


def detect_deleted_files(pdf_paths: list[Path]) -> list[Path]:
    current_paths = {str(path) for path in pdf_paths}
    return [
        Path(record["file_path"])
        for record in fetch_all_file_records(FILE_TRACKING_DB_PATH)
        if record["is_present"] and record["file_path"] not in current_paths
    ]


def confirm_force_rebuild(assume_yes: bool) -> None:
    if assume_yes:
        return
    print("Clean rebuild requested.")
    print("This deletes generated indexes and metadata, then rebuilds them from data/.")
    if input("Continue with clean rebuild? (y/n) ").strip().lower() != "y":
        print("Ingestion cancelled. Existing storage was not changed.")
        sys.exit(0)


def confirm_changes(change_count: int, deleted_count: int, assume_yes: bool) -> None:
    if change_count == 0 or assume_yes:
        return
    print(f"Found {change_count} source changes ({deleted_count} deletions).")
    print("Changed chunks invalidate existing model indexes, which will be rebuilt.")
    if input("Proceed? (y/n) ").strip().lower() != "y":
        print("Ingestion cancelled.")
        sys.exit(0)


def record_current_files_seen(seen_files: list[dict]) -> None:
    for file_info in seen_files:
        record_file_seen(FILE_TRACKING_DB_PATH, str(file_info["path"]), file_info["hash"])


def process_pdf(pdf_path: Path, file_hash: str) -> int:
    print(f"Chunking: {pdf_path}")
    chunks = CHUNKERS[".pdf"].chunk_pages(load_pdf_pages(pdf_path))
    print(f"Created {len(chunks)} chunks.")
    document_id = str(pdf_path)
    delete_document_chunks(METADATA_DB_PATH, document_id)
    if not chunks:
        upsert_file_record(FILE_TRACKING_DB_PATH, str(pdf_path), file_hash)
        return 0

    ingestion_timestamp = utc_now_iso()
    rows = [
        {
            "chunk_id": str(uuid4()),
            "document_id": document_id,
            "source_path": str(pdf_path),
            "file_type": ".pdf",
            "title": chunk["title"],
            "chunk_text": chunk["chunk_text"],
            "chunk_index": chunk["chunk_index"],
            "page_number": chunk["page_number"],
            "paragraph_index": chunk["paragraph_index"],
            "paragraph_text": chunk["paragraph_text"],
            "section_heading": chunk["section_heading"],
            "ingestion_timestamp": ingestion_timestamp,
        }
        for chunk in chunks
    ]
    insert_chunk_rows(METADATA_DB_PATH, rows)
    upsert_file_record(FILE_TRACKING_DB_PATH, str(pdf_path), file_hash)
    return len(rows)


def synchronize_chunks(
    files_to_process: list[dict], deleted_paths: list[Path], seen_files: list[dict]
) -> tuple[int, int]:
    if not files_to_process and not deleted_paths:
        return 0, 0

    clear_all_index_metadata(METADATA_DB_PATH)
    clear_generated_indexes()

    for deleted_path in deleted_paths:
        print(f"Deleting removed source: {deleted_path}")
        delete_document_chunks(METADATA_DB_PATH, str(deleted_path))
        mark_file_deleted(FILE_TRACKING_DB_PATH, str(deleted_path))

    processed_chunks = 0
    for position, file_info in enumerate(files_to_process, start=1):
        print(
            f"[{position}/{len(files_to_process)}] "
            f"{file_info['status']}: {file_info['path']}"
        )
        processed_chunks += process_pdf(file_info["path"], file_info["hash"])
    record_current_files_seen(seen_files)
    return processed_chunks, len(deleted_paths)


def index_needs_build(model_alias: str) -> bool:
    index_id = make_index_id(model_alias)
    path = faiss_index_path(model_alias)
    record = get_index_record(METADATA_DB_PATH, index_id)
    if record is None or not path.exists():
        return True
    chunk_count = count_chunks(METADATA_DB_PATH)
    return (
        int(record["chunk_count"]) != chunk_count
        or count_index_entries(METADATA_DB_PATH, index_id) != chunk_count
    )


def build_model_index(model_alias: str) -> None:
    model_started_at = perf_counter()
    config = get_embedding_model(model_alias)
    rows = fetch_all_chunks(METADATA_DB_PATH)
    if not rows:
        raise SystemExit("No chunks are available to index. Add PDFs under data/ first.")

    print(f"Loading {config.display_name} ({config.model_id})...")
    load_started_at = perf_counter()
    embedder = TextEmbedder(config)
    load_seconds = perf_counter() - load_started_at
    print(f"Loaded {model_alias} in {load_seconds:.2f}s.")

    print(f"Embedding {len(rows)} chunks on {embedder.device}...")
    embedding_started_at = perf_counter()
    embeddings = embedder.embed_texts(
        [row["chunk_text"] for row in rows], input_type="document"
    )
    embedding_seconds = perf_counter() - embedding_started_at
    chunks_per_second = len(rows) / embedding_seconds if embedding_seconds else 0.0
    print(
        f"Embedded {len(rows)} chunks in {embedding_seconds:.2f}s "
        f"({chunks_per_second:.1f} chunks/s)."
    )

    index_started_at = perf_counter()
    vector_ids = np.arange(len(rows), dtype=np.int64)
    index = faiss.IndexIDMap2(faiss.IndexFlatIP(embedder.get_embedding_dimension()))
    index.add_with_ids(embeddings, vector_ids)

    path = faiss_index_path(model_alias)
    path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(path))
    index_id = make_index_id(model_alias)
    replace_index(
        METADATA_DB_PATH,
        index_id=index_id,
        chunker_alias=DEFAULT_CHUNKER_ALIAS,
        model_alias=model_alias,
        embedding_model=config.model_id,
        dimensions=embedder.get_embedding_dimension(),
        chunk_count=len(rows),
        index_path=str(path.relative_to(STORAGE_DIR)),
        chunk_ids=[row["chunk_id"] for row in rows],
    )
    index_seconds = perf_counter() - index_started_at
    total_seconds = perf_counter() - model_started_at
    print(
        f"Saved {model_alias} index ({len(rows)} vectors) to {path} "
        f"in {index_seconds:.2f}s."
    )
    print(f"Completed {model_alias} in {total_seconds:.2f}s total.")


def main() -> None:
    args = parse_args()
    selected_models = resolve_model_aliases(args.model)
    ensure_directories()

    if args.force_rebuild:
        confirm_force_rebuild(args.yes)
        reset_storage()

    initialize_metadata_db(METADATA_DB_PATH)
    initialize_file_tracking_db(FILE_TRACKING_DB_PATH)

    pdf_paths = discover_pdf_files()
    files_to_process, seen_files = detect_files_to_process(pdf_paths)
    deleted_paths = detect_deleted_files(pdf_paths)
    change_count = len(files_to_process) + len(deleted_paths)
    confirm_changes(
        change_count,
        len(deleted_paths),
        assume_yes=args.yes or args.force_rebuild,
    )
    processed_chunks, deleted_files = synchronize_chunks(
        files_to_process, deleted_paths, seen_files
    )

    models_to_build = [
        alias for alias in selected_models if args.force_rebuild or index_needs_build(alias)
    ]
    if not change_count and not models_to_build:
        print("Chunks and selected model indexes are already current. Nothing to do.")
        return

    for model_alias in models_to_build:
        build_model_index(model_alias)

    print("Ingestion complete.")
    print(f"Processed files: {len(files_to_process)}")
    print(f"Deleted files: {deleted_files}")
    print(f"New chunks this run: {processed_chunks}")
    print(f"Total stored chunks: {count_chunks(METADATA_DB_PATH)}")
    print(f"Built models: {', '.join(models_to_build) if models_to_build else 'none'}")


if __name__ == "__main__":
    main()
