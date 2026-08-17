from __future__ import annotations

import hashlib
from dataclasses import asdict
from pathlib import Path

from evaluation.artifacts import append_jsonl, create_run_directory, summarize_results, utc_now, write_json
from evaluation.benchmark import ExperimentSpec, GenerationCase
from evaluation.conditions import ArcticRetriever, prepare_condition
from evaluation.scoring import score_answer
from generation.ollama_provider import OllamaProvider


def _serialize_sources(sources) -> list[dict]:
    return [asdict(source) for source in sources]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _attempt_record(
    *,
    condition: str,
    case: GenerationCase,
    repetition: int,
    prepared,
    result,
) -> dict:
    available_labels = {source.label for source in prepared.sources}
    score = score_answer(
        case,
        result.content,
        condition=condition,
        available_source_labels=available_labels,
    )
    return {
        "status": "completed",
        "completed_at": utc_now(),
        "case_id": case.case_id,
        "question": case.question,
        "task_type": case.task_type,
        "answerability": case.answerability,
        "condition": condition,
        "repetition": repetition,
        "answer": result.content,
        "sources": _serialize_sources(prepared.sources),
        "retrieval_evidence_hit": prepared.retrieval_evidence_hit,
        "score": score,
        "timing": {
            "context_seconds": prepared.context_seconds,
            "generation_seconds": result.wall_seconds,
            "first_token_seconds": result.first_token_seconds,
        },
        "usage": {
            "prompt_tokens": result.usage.prompt_tokens,
            "output_tokens": result.usage.output_tokens,
            "total_tokens": result.usage.total_tokens,
            "ollama_total_seconds": result.usage.total_duration_seconds,
            "model_load_seconds": result.usage.load_duration_seconds,
            "prompt_eval_seconds": result.usage.prompt_eval_duration_seconds,
            "generation_eval_seconds": result.usage.generation_duration_seconds,
            "output_tokens_per_second": result.usage.output_tokens_per_second,
        },
        "done_reason": result.done_reason,
    }


def run_evaluation(
    *,
    spec: ExperimentSpec,
    cases: list[GenerationCase],
    conditions: list[str],
    repetitions: int,
    model: str,
    url: str,
    runs_root: Path,
    canonical: bool,
    input_files: dict[str, Path],
) -> tuple[Path, dict]:
    run_directory = create_run_directory(runs_root)
    results_path = run_directory / "results.jsonl"
    manifest = {
        "started_at": utc_now(),
        "canonical": canonical,
        "experiment_id": spec.experiment_id,
        "benchmark_id": spec.benchmark_id,
        "model": model,
        "prompt_version": spec.prompt_version,
        "conditions": conditions,
        "case_ids": [case.case_id for case in cases],
        "top_k": spec.top_k,
        "repetitions": repetitions,
        "timeout_seconds": spec.timeout_seconds,
        "input_sha256": {
            name: _sha256(path) for name, path in input_files.items()
        },
    }
    write_json(run_directory / "manifest.json", manifest)

    provider = OllamaProvider(
        model, url=url, timeout_seconds=spec.timeout_seconds
    )
    retriever = ArcticRetriever() if "dense_rag:arctic" in conditions else None
    records: list[dict] = []
    total_attempts = len(cases) * len(conditions) * repetitions
    attempt_number = 0

    for case in cases:
        for condition in conditions:
            for repetition in range(1, repetitions + 1):
                attempt_number += 1
                print(
                    f"[{attempt_number}/{total_attempts}] {case.case_id} / "
                    f"{condition} / repetition {repetition}"
                )
                try:
                    prepared = prepare_condition(
                        condition,
                        case,
                        top_k=spec.top_k,
                        retriever=retriever,
                    )
                    result = provider.chat(prepared.messages, stream=False)
                    record = _attempt_record(
                        condition=condition,
                        case=case,
                        repetition=repetition,
                        prepared=prepared,
                        result=result,
                    )
                    verdict = "PASS" if record["score"]["passed"] else "FAIL"
                    print(
                        f"  {verdict}: {result.content[:160].replace(chr(10), ' ')}"
                    )
                except Exception as error:  # Preserve the rest of a long run.
                    record = {
                        "status": "error",
                        "completed_at": utc_now(),
                        "case_id": case.case_id,
                        "question": case.question,
                        "task_type": case.task_type,
                        "answerability": case.answerability,
                        "condition": condition,
                        "repetition": repetition,
                        "error_type": type(error).__name__,
                        "error": str(error),
                    }
                    print(f"  ERROR: {type(error).__name__}: {error}")

                records.append(record)
                append_jsonl(results_path, record)

    summary = summarize_results(records)
    write_json(run_directory / "summary.json", summary)
    return run_directory, summary
