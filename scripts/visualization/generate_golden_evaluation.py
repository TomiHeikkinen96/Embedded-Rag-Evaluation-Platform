from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import faiss

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from processing.embedder import TextEmbedder
from processing.embedding_models import EMBEDDING_MODELS, get_embedding_model
from project_paths import METADATA_DB_PATH, PROJECT_ROOT, VISUALIZATION_DIR, faiss_index_path
from search_index import search_query
from utils.db import initialize_metadata_db, make_index_id

BENCHMARK_DIR = PROJECT_ROOT / "benchmarks" / "esp32-retrieval-v1"
OUTPUT_PATH = VISUALIZATION_DIR / "golden-evaluation.json"
EVALUATION_DEPTH = 10


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalized_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def path_matches(source_path: str, expected_path: str) -> bool:
    return Path(source_path).name == Path(expected_path).name


def label_result(row: dict, evidence: list[dict], documents: dict[str, dict]) -> str:
    result_text = normalized_text(
        f"{row['chunk_text']} {row['paragraph_text'] or ''}"
    )
    page_match = False
    for item in evidence:
        document = documents[item["document_id"]]
        if not path_matches(row["source_path"], document["path"]):
            continue
        if row["page_number"] != item["pdf_page"]:
            continue
        page_match = True
        if normalized_text(item["text_anchor"]) in result_text:
            return "evidence"
    return "source_page" if page_match else "miss"


def recall_at(rank: int | None, depth: int) -> float:
    return 1.0 if rank is not None and rank <= depth else 0.0


def evaluate_model(model_alias: str, cases: list[dict], documents: dict[str, dict]) -> dict:
    config = get_embedding_model(model_alias)
    index_path = faiss_index_path(model_alias)
    if not index_path.exists():
        return {
            "alias": model_alias,
            "display_name": config.display_name,
            "available": False,
            "reason": f"Missing index: {index_path.relative_to(PROJECT_ROOT)}",
        }

    index = faiss.read_index(str(index_path))
    embedder = TextEmbedder(config)
    index_id = make_index_id(model_alias)
    evaluated_cases = []

    for case in cases:
        ranked_results = search_query(
            case["question"], index, embedder, index_id, top_k=EVALUATION_DEPTH
        )
        results = []
        first_evidence_rank = None
        first_source_page_rank = None
        for rank, result in enumerate(ranked_results, start=1):
            row = result["row"]
            label = label_result(row, case["evidence"], documents)
            if label == "evidence" and first_evidence_rank is None:
                first_evidence_rank = rank
            if label in {"evidence", "source_page"} and first_source_page_rank is None:
                first_source_page_rank = rank
            results.append(
                {
                    "rank": rank,
                    "label": label,
                    "source_path": row["source_path"],
                    "page": row["page_number"],
                    "chunk": " ".join(row["chunk_text"].split())[:260],
                    "semantic_score": round(result["semantic_score"], 4),
                    "rerank_score": round(result["rerank_score"], 4),
                }
            )

        evaluated_cases.append(
            {
                "id": case["id"],
                "question": case["question"],
                "task_type": case["task_type"],
                "expected_answer_note": case["expected_answer_note"],
                "evidence": case["evidence"],
                "first_evidence_rank": first_evidence_rank,
                "first_source_page_rank": first_source_page_rank,
                "reciprocal_rank": round(1 / first_evidence_rank, 4)
                if first_evidence_rank
                else 0.0,
                "results": results,
            }
        )

    count = len(evaluated_cases)
    mean = lambda values: round(sum(values) / count, 4) if count else 0.0
    return {
        "alias": model_alias,
        "display_name": config.display_name,
        "available": True,
        "metrics": {
            "case_count": count,
            "mrr": mean([case["reciprocal_rank"] for case in evaluated_cases]),
            "recall_at_1": mean(
                [recall_at(case["first_evidence_rank"], 1) for case in evaluated_cases]
            ),
            "recall_at_3": mean(
                [recall_at(case["first_evidence_rank"], 3) for case in evaluated_cases]
            ),
            "recall_at_5": mean(
                [recall_at(case["first_evidence_rank"], 5) for case in evaluated_cases]
            ),
            "recall_at_10": mean(
                [recall_at(case["first_evidence_rank"], 10) for case in evaluated_cases]
            ),
        },
        "cases": evaluated_cases,
    }


def main() -> None:
    initialize_metadata_db(METADATA_DB_PATH)
    corpus = load_json(BENCHMARK_DIR / "corpus.json")
    benchmark = load_json(BENCHMARK_DIR / "cases.json")
    documents = {document["document_id"]: document for document in corpus["documents"]}
    active_cases = [case for case in benchmark["cases"] if case["status"] == "active"]
    payload = {
        "benchmark_id": benchmark["benchmark_id"],
        "corpus_id": benchmark["corpus_id"],
        "evaluation_depth": EVALUATION_DEPTH,
        "label_definition": "A hit requires the labelled document, physical PDF page, and normalized text anchor in the retrieved chunk or display paragraph.",
        "models": [
            evaluate_model(alias, active_cases, documents) for alias in EMBEDDING_MODELS
        ],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    available = [model for model in payload["models"] if model["available"]]
    print(f"Wrote {len(active_cases)} golden cases for {len(available)} models to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
