from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_run_directory(runs_root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")
    run_directory = runs_root / timestamp
    run_directory.mkdir(parents=True, exist_ok=False)
    return run_directory


def write_json(path: Path, value: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def append_jsonl(path: Path, value: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def summarize_results(records: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[record["condition"]].append(record)

    conditions = {}
    for condition, items in grouped.items():
        completed = [item for item in items if item.get("status") == "completed"]
        errors = len(items) - len(completed)
        usage_items = [item["usage"] for item in completed]

        def rate(field: str, selected: list[dict] | None = None) -> float | None:
            relevant = completed if selected is None else selected
            if not relevant:
                return None
            return sum(bool(item["score"][field]) for item in relevant) / len(relevant)

        unanswerable = [
            item for item in completed if item["answerability"] == "unanswerable"
        ]
        citation_required = [
            item for item in completed if item["score"]["citation_required"]
        ]
        retrieval_scored = [
            item
            for item in completed
            if item.get("retrieval_evidence_hit") is not None
        ]

        conditions[condition] = {
            "attempts": len(items),
            "completed": len(completed),
            "errors": errors,
            "pass_rate": rate("passed"),
            "answer_accuracy": rate("answer_correct"),
            "citation_validity_rate": rate("citations_valid", citation_required),
            "unanswerable_refusal_rate": rate("refusal_intent", unanswerable),
            "unanswerable_exact_refusal_rate": rate("exact_refusal", unanswerable),
            "retrieval_evidence_hit_rate": (
                sum(bool(item["retrieval_evidence_hit"]) for item in retrieval_scored)
                / len(retrieval_scored)
                if retrieval_scored
                else None
            ),
            "average_context_seconds": (
                sum(item["timing"]["context_seconds"] for item in completed)
                / len(completed)
                if completed
                else None
            ),
            "average_generation_seconds": (
                sum(item["timing"]["generation_seconds"] for item in completed)
                / len(completed)
                if completed
                else None
            ),
            "total_prompt_tokens": sum(item["prompt_tokens"] for item in usage_items),
            "total_output_tokens": sum(item["output_tokens"] for item in usage_items),
        }

    return {
        "created_at": utc_now(),
        "attempts": len(records),
        "completed": sum(record.get("status") == "completed" for record in records),
        "errors": sum(record.get("status") == "error" for record in records),
        "conditions": conditions,
    }
