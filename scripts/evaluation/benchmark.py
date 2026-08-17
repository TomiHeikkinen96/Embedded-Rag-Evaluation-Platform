from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_CONDITIONS = {"closed_book", "oracle", "dense_rag:arctic"}


@dataclass(frozen=True)
class GenerationCase:
    case_id: str
    question: str
    task_type: str
    answerability: str
    required_facts: list[dict]
    oracle_sources: list[dict]


@dataclass(frozen=True)
class ExperimentSpec:
    experiment_id: str
    benchmark_id: str
    model: str
    prompt_version: str
    conditions: list[str]
    top_k: int
    repetitions: int
    timeout_seconds: int


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_benchmark(benchmark_dir: Path) -> tuple[ExperimentSpec, list[GenerationCase]]:
    experiment_data = _load_json(benchmark_dir / "experiment.json")
    cases_data = _load_json(benchmark_dir / "cases.json")

    spec = ExperimentSpec(
        experiment_id=experiment_data["experiment_id"],
        benchmark_id=experiment_data["benchmark_id"],
        model=experiment_data["model"],
        prompt_version=experiment_data["prompt_version"],
        conditions=list(experiment_data["conditions"]),
        top_k=int(experiment_data["top_k"]),
        repetitions=int(experiment_data["repetitions"]),
        timeout_seconds=int(experiment_data["timeout_seconds"]),
    )
    cases = [
        GenerationCase(
            case_id=item["id"],
            question=item["question"],
            task_type=item["task_type"],
            answerability=item["answerability"],
            required_facts=list(item.get("required_facts", [])),
            oracle_sources=list(item.get("oracle_sources", [])),
        )
        for item in cases_data["cases"]
    ]
    _validate(spec, cases_data, cases)
    return spec, cases


def _validate(
    spec: ExperimentSpec, cases_data: dict, cases: list[GenerationCase]
) -> None:
    errors: list[str] = []
    if cases_data.get("benchmark_id") != spec.benchmark_id:
        errors.append("experiment and cases benchmark_id values differ")
    if spec.top_k < 1:
        errors.append("top_k must be at least 1")
    if spec.repetitions < 1:
        errors.append("repetitions must be at least 1")
    unknown_conditions = set(spec.conditions) - SUPPORTED_CONDITIONS
    if unknown_conditions:
        errors.append(f"unsupported conditions: {sorted(unknown_conditions)}")

    seen_ids: set[str] = set()
    for case in cases:
        if case.case_id in seen_ids:
            errors.append(f"duplicate case id: {case.case_id}")
        seen_ids.add(case.case_id)
        if case.answerability not in {"answerable", "unanswerable"}:
            errors.append(f"{case.case_id}: invalid answerability")
        if case.answerability == "answerable" and not case.required_facts:
            errors.append(f"{case.case_id}: answerable case has no required facts")
        if case.answerability == "answerable" and not case.oracle_sources:
            errors.append(f"{case.case_id}: answerable case has no oracle sources")
        for fact in case.required_facts:
            if not fact.get("name") or not fact.get("accepted"):
                errors.append(f"{case.case_id}: invalid required fact")

    if errors:
        raise ValueError("Invalid generation benchmark:\n- " + "\n- ".join(errors))
