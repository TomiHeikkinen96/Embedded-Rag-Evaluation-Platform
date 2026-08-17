from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.benchmark import SUPPORTED_CONDITIONS, load_benchmark
from evaluation.runner import run_evaluation
from generation.ollama_provider import DEFAULT_OLLAMA_CHAT_URL
from project_paths import PROJECT_ROOT


DEFAULT_BENCHMARK_DIR = PROJECT_ROOT / "benchmarks" / "esp32-generation-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the committed closed-book, oracle, and Arctic RAG evaluation."
    )
    parser.add_argument(
        "--benchmark-dir", type=Path, default=DEFAULT_BENCHMARK_DIR
    )
    parser.add_argument(
        "--condition",
        action="append",
        choices=sorted(SUPPORTED_CONDITIONS),
        help="Run only this condition. Repeat to select several.",
    )
    parser.add_argument(
        "--case", action="append", help="Run only this case id. Repeat to select several."
    )
    parser.add_argument("--repetitions", type=int, help="Override repetitions for a development run.")
    parser.add_argument("--model", help="Override the Ollama model for a development run.")
    parser.add_argument("--url", default=DEFAULT_OLLAMA_CHAT_URL)
    return parser.parse_args()


def _print_summary(summary: dict) -> None:
    print("\nSummary:")
    for condition, metrics in summary["conditions"].items():
        pass_rate = metrics["pass_rate"]
        pass_text = "n/a" if pass_rate is None else f"{pass_rate:.1%}"
        print(
            f"  {condition:<18} pass={pass_text:>6}  "
            f"completed={metrics['completed']}/{metrics['attempts']}  "
            f"errors={metrics['errors']}"
        )


def main() -> int:
    args = parse_args()
    benchmark_dir = args.benchmark_dir
    if not benchmark_dir.is_absolute():
        benchmark_dir = PROJECT_ROOT / benchmark_dir
    spec, all_cases = load_benchmark(benchmark_dir)

    conditions = args.condition or spec.conditions
    selected_case_ids = set(args.case or [])
    cases = [case for case in all_cases if not selected_case_ids or case.case_id in selected_case_ids]
    missing_cases = selected_case_ids - {case.case_id for case in cases}
    if missing_cases:
        raise SystemExit(f"Unknown case ids: {', '.join(sorted(missing_cases))}")
    repetitions = args.repetitions if args.repetitions is not None else spec.repetitions
    if repetitions < 1:
        raise SystemExit("--repetitions must be at least 1")
    model = args.model or spec.model
    canonical = (
        benchmark_dir.resolve() == DEFAULT_BENCHMARK_DIR.resolve()
        and args.url == DEFAULT_OLLAMA_CHAT_URL
        and not any(
            [args.condition, args.case, args.repetitions is not None, args.model]
        )
    )

    print(
        f"Running {len(cases)} cases x {len(conditions)} conditions x "
        f"{repetitions} repetitions with {model}."
    )
    print(f"Run type: {'canonical' if canonical else 'filtered/non-canonical'}")
    run_directory, summary = run_evaluation(
        spec=spec,
        cases=cases,
        conditions=conditions,
        repetitions=repetitions,
        model=model,
        url=args.url,
        runs_root=PROJECT_ROOT / "runs" / "generation",
        canonical=canonical,
        input_files={
            "experiment.json": benchmark_dir / "experiment.json",
            "cases.json": benchmark_dir / "cases.json",
            "Modelfile": PROJECT_ROOT / "Modelfile",
        },
    )
    _print_summary(summary)
    print(f"\nArtifacts: {run_directory}")
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
