from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

try:
    import fitz
except ImportError as exc:
    raise ImportError(
        "PyMuPDF is required for benchmark validation. Install dependencies with "
        "`pip install -r requirements.txt`."
    ) from exc

from project_paths import PROJECT_ROOT


DEFAULT_BENCHMARK_DIR = PROJECT_ROOT / "benchmarks" / "esp32-retrieval-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate corpus hashes and source-evidence anchors."
    )
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=DEFAULT_BENCHMARK_DIR,
        help="Directory containing corpus.json and cases.json.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_text(value: str) -> str:
    # PDF table extraction can vary in whitespace and punctuation across readers.
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def validate() -> list[str]:
    args = parse_args()
    benchmark_dir = args.benchmark_dir
    if not benchmark_dir.is_absolute():
        benchmark_dir = PROJECT_ROOT / benchmark_dir

    corpus = load_json(benchmark_dir / "corpus.json")
    benchmark = load_json(benchmark_dir / "cases.json")
    errors: list[str] = []

    if benchmark.get("corpus_id") != corpus.get("corpus_id"):
        errors.append("cases.json corpus_id does not match corpus.json")

    documents = {item["document_id"]: item for item in corpus["documents"]}
    open_documents: dict[str, fitz.Document] = {}

    try:
        for document_id, metadata in documents.items():
            path = PROJECT_ROOT / metadata["path"]
            if not path.exists():
                errors.append(f"{document_id}: missing file {metadata['path']}")
                continue
            actual_hash = sha256(path)
            if actual_hash != metadata["sha256"]:
                errors.append(f"{document_id}: SHA-256 mismatch")
            document = fitz.open(path)
            open_documents[document_id] = document
            if document.page_count != metadata["pdf_pages"]:
                errors.append(
                    f"{document_id}: expected {metadata['pdf_pages']} pages, "
                    f"found {document.page_count}"
                )

        seen_case_ids: set[str] = set()
        for case in benchmark["cases"]:
            case_id = case["id"]
            if case_id in seen_case_ids:
                errors.append(f"duplicate case id: {case_id}")
            seen_case_ids.add(case_id)

            if case["status"] == "active" and not case.get("evidence"):
                errors.append(f"{case_id}: active case has no evidence")

            for evidence in case.get("evidence", []):
                document_id = evidence["document_id"]
                document = open_documents.get(document_id)
                if document is None:
                    errors.append(f"{case_id}: unknown or unavailable {document_id}")
                    continue
                pdf_page = evidence["pdf_page"]
                if not 1 <= pdf_page <= document.page_count:
                    errors.append(f"{case_id}: invalid PDF page {pdf_page}")
                    continue
                page_text = document.load_page(pdf_page - 1).get_text("text")
                if normalized_text(evidence["text_anchor"]) not in normalized_text(page_text):
                    errors.append(
                        f"{case_id}: anchor not found in {document_id} PDF page {pdf_page}: "
                        f"{evidence['text_anchor']!r}"
                    )
    finally:
        for document in open_documents.values():
            document.close()

    return errors


def main() -> None:
    errors = validate()
    if errors:
        print("Benchmark validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("Benchmark validation passed: corpus hashes, pages, and anchors resolve.")


if __name__ == "__main__":
    main()
