from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from evaluation.artifacts import summarize_results
from project_paths import PROJECT_ROOT, VISUALIZATION_DIR


DEFAULT_RUNS_ROOT = PROJECT_ROOT / "runs" / "generation"
DEFAULT_OUTPUT_PATH = VISUALIZATION_DIR / "generation-evaluation.json"
MAX_EXPORTED_RUNS = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export generation runs as browser-ready evaluation data."
    )
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--max-runs", type=int, default=MAX_EXPORTED_RUNS)
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


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    warnings: list[str] = []
    if not path.exists():
        return records, warnings

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                warnings.append(
                    f"Ignored incomplete JSONL line {line_number}; the run may still be writing."
                )
    return records, warnings


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def enrich_summary(summary: dict, records: list[dict]) -> dict:
    enriched = deepcopy(summary)
    completed = [record for record in records if record.get("status") == "completed"]
    oracle_records = [
        record for record in completed if record["condition"] == "oracle"
    ]
    oracle_pipeline_seconds = mean(
        [
            record["timing"]["context_seconds"]
            + record["timing"]["generation_seconds"]
            for record in oracle_records
        ]
    )

    for condition, metrics in enriched.get("conditions", {}).items():
        items = [record for record in completed if record["condition"] == condition]
        pipeline_seconds = mean(
            [
                record["timing"]["context_seconds"]
                + record["timing"]["generation_seconds"]
                for record in items
            ]
        )
        metrics["average_pipeline_seconds"] = pipeline_seconds
        metrics["average_prompt_tokens"] = mean(
            [record["usage"]["prompt_tokens"] for record in items]
        )
        metrics["average_output_tokens"] = mean(
            [record["usage"]["output_tokens"] for record in items]
        )
        metrics["average_output_tokens_per_second"] = mean(
            [record["usage"]["output_tokens_per_second"] for record in items]
        )
        metrics["oracle_pipeline_delta_seconds"] = (
            pipeline_seconds - oracle_pipeline_seconds
            if pipeline_seconds is not None and oracle_pipeline_seconds is not None
            else None
        )
        metrics["oracle_pipeline_ratio"] = (
            pipeline_seconds / oracle_pipeline_seconds
            if pipeline_seconds is not None
            and oracle_pipeline_seconds not in {None, 0}
            else None
        )
    return enriched


def export_run(run_directory: Path) -> dict | None:
    manifest_path = run_directory / "manifest.json"
    if not manifest_path.exists():
        return None

    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as error:
        return {
            "run_id": run_directory.name,
            "available": False,
            "reason": f"Could not read manifest: {error}",
        }

    records, warnings = load_jsonl(run_directory / "results.jsonl")
    expected_attempts = (
        len(manifest.get("case_ids", []))
        * len(manifest.get("conditions", []))
        * int(manifest.get("repetitions", 1))
    )
    summary_path = run_directory / "summary.json"
    finalized = summary_path.exists()
    try:
        summary = load_json(summary_path) if finalized else summarize_results(records)
    except (OSError, json.JSONDecodeError) as error:
        warnings.append(f"Could not read final summary; derived it from JSONL: {error}")
        summary = summarize_results(records)
        finalized = False

    observed_attempts = len(records)
    complete = finalized and observed_attempts >= expected_attempts
    if complete and summary.get("errors", 0):
        state = "complete_with_errors"
    elif complete:
        state = "complete"
    else:
        state = "partial"

    return {
        "run_id": run_directory.name,
        "available": True,
        "state": state,
        "finalized": finalized,
        "expected_attempts": expected_attempts,
        "observed_attempts": observed_attempts,
        "progress": observed_attempts / expected_attempts if expected_attempts else 0.0,
        "warnings": warnings,
        "manifest": manifest,
        "summary": enrich_summary(summary, records),
        "records": records,
    }


def select_default_run(runs: list[dict]) -> str | None:
    available = [run for run in runs if run.get("available")]
    for run in available:
        if run["manifest"].get("canonical") and run["state"].startswith("complete"):
            return run["run_id"]
    for run in available:
        if run["state"].startswith("complete"):
            return run["run_id"]
    return available[0]["run_id"] if available else None


def generate_payload(runs_root: Path, max_runs: int) -> dict:
    run_directories = (
        sorted(
            (path for path in runs_root.iterdir() if path.is_dir()),
            reverse=True,
        )
        if runs_root.exists()
        else []
    )
    runs = [
        exported
        for run_directory in run_directories[:max_runs]
        if (exported := export_run(run_directory)) is not None
    ]
    runs.sort(
        key=lambda run: (
            run.get("manifest", {}).get("started_at") or run.get("run_id", "")
        ),
        reverse=True,
    )
    current_inputs = {
        "experiment.json": PROJECT_ROOT
        / "benchmarks"
        / "esp32-generation-v1"
        / "experiment.json",
        "cases.json": PROJECT_ROOT
        / "benchmarks"
        / "esp32-generation-v1"
        / "cases.json",
        "Modelfile": PROJECT_ROOT / "Modelfile",
    }
    current_hashes = {
        name: sha256(path) for name, path in current_inputs.items() if path.exists()
    }
    for run in runs:
        if not run.get("available"):
            continue
        recorded_hashes = run["manifest"].get("input_sha256", {})
        run["input_drift"] = [
            name
            for name, current_hash in current_hashes.items()
            if recorded_hashes.get(name) not in {None, current_hash}
        ]
    selected_run_id = select_default_run(runs)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "available": selected_run_id is not None,
        "reason": None if selected_run_id else "No generation evaluation runs found.",
        "selected_run_id": selected_run_id,
        "current_input_sha256": current_hashes,
        "runs": runs,
    }


def main() -> None:
    args = parse_args()
    if args.max_runs < 1:
        raise SystemExit("--max-runs must be at least 1")
    payload = generate_payload(args.runs_root, args.max_runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    available_runs = sum(run.get("available", False) for run in payload["runs"])
    print(
        f"Wrote {available_runs} generation runs to {args.output}; "
        f"default={payload['selected_run_id'] or 'none'}"
    )


if __name__ == "__main__":
    main()
