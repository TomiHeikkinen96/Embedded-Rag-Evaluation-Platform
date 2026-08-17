from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from visualization.generate_generation_evaluation import (  # noqa: E402
    enrich_summary,
    generate_payload,
)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


class GenerationVisualizationTests(unittest.TestCase):
    def manifest(self, *, canonical: bool) -> dict:
        return {
            "canonical": canonical,
            "model": "rageval-qwen",
            "conditions": ["closed_book", "oracle"],
            "case_ids": ["case-one"],
            "repetitions": 1,
        }

    def completed_record(self, condition: str) -> dict:
        return {
            "status": "completed",
            "condition": condition,
            "case_id": "case-one",
            "question": "Question?",
            "answerability": "answerable",
            "score": {
                "passed": True,
                "answer_correct": True,
                "fact_results": [
                    {"name": "required value", "matched": True, "matched_variant": "5"}
                ],
                "citations_valid": True,
                "citation_required": condition == "oracle",
                "refusal_intent": False,
                "exact_refusal": False,
            },
            "retrieval_evidence_hit": None,
            "timing": {"context_seconds": 0.1, "generation_seconds": 1.0},
            "usage": {
                "prompt_tokens": 10,
                "output_tokens": 5,
                "output_tokens_per_second": 5.0,
            },
        }

    def test_partial_run_is_exported_without_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / "2026-01-01T00-00-00Z"
            run.mkdir()
            write_json(run / "manifest.json", self.manifest(canonical=True))
            (run / "results.jsonl").write_text(
                json.dumps(self.completed_record("closed_book")) + "\n",
                encoding="utf-8",
            )

            payload = generate_payload(Path(directory), max_runs=5)

            self.assertTrue(payload["available"])
            self.assertEqual(payload["runs"][0]["state"], "partial")
            self.assertEqual(payload["runs"][0]["observed_attempts"], 1)
            self.assertEqual(payload["runs"][0]["expected_attempts"], 2)
            metrics = payload["runs"][0]["summary"]["conditions"]["closed_book"]
            self.assertEqual(metrics["average_prompt_tokens"], 10)
            self.assertEqual(metrics["average_output_tokens"], 5)
            self.assertEqual(metrics["average_total_tokens"], 15)
            self.assertEqual(metrics["total_prompt_tokens"], 10)
            self.assertEqual(metrics["total_output_tokens"], 5)
            self.assertEqual(metrics["total_tokens"], 15)
            self.assertEqual(metrics["required_facts_matched"], 1)
            self.assertEqual(metrics["required_facts_expected"], 1)
            self.assertEqual(metrics["required_fact_coverage_rate"], 1.0)
            self.assertEqual(metrics["corpus_negative_attempts"], 0)
            self.assertEqual(metrics["unsupported_claims_evaluation"], "manual_review")

    def test_latest_complete_canonical_run_is_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "2026-01-01T00-00-00Z"
            filtered = root / "2026-01-02T00-00-00Z"
            for run, is_canonical in ((canonical, True), (filtered, False)):
                run.mkdir()
                write_json(run / "manifest.json", self.manifest(canonical=is_canonical))
                records = [
                    self.completed_record("closed_book"),
                    self.completed_record("oracle"),
                ]
                (run / "results.jsonl").write_text(
                    "".join(json.dumps(record) + "\n" for record in records),
                    encoding="utf-8",
                )
                write_json(
                    run / "summary.json",
                    {
                        "attempts": 2,
                        "completed": 2,
                        "errors": 0,
                        "conditions": {
                            condition: {
                                "attempts": 1,
                                "completed": 1,
                                "errors": 0,
                                "pass_rate": 1.0,
                                "answer_accuracy": 1.0,
                                "citation_validity_rate": 1.0,
                                "unanswerable_refusal_rate": None,
                                "unanswerable_exact_refusal_rate": None,
                                "retrieval_evidence_hit_rate": None,
                                "average_context_seconds": 0.1,
                                "average_generation_seconds": 1.0,
                                "total_prompt_tokens": 10,
                                "total_output_tokens": 5,
                            }
                            for condition in ("closed_book", "oracle")
                        },
                    },
                )

            payload = generate_payload(root, max_runs=5)

            self.assertEqual(payload["selected_run_id"], canonical.name)
            self.assertEqual(
                [run["run_id"] for run in payload["runs"]],
                [filtered.name, canonical.name],
            )

    def test_enriched_summary_separates_corpus_negative_refusal(self) -> None:
        record = self.completed_record("oracle")
        record["answerability"] = "unanswerable"
        record["score"]["fact_results"] = []
        record["score"]["refusal_intent"] = True
        record["score"]["exact_refusal"] = False
        summary = {
            "conditions": {
                "oracle": {
                    "unanswerable_refusal_rate": 1.0,
                    "unanswerable_exact_refusal_rate": 0.0,
                }
            }
        }

        metrics = enrich_summary(summary, [record])["conditions"]["oracle"]

        self.assertEqual(metrics["required_facts_expected"], 0)
        self.assertIsNone(metrics["required_fact_coverage_rate"])
        self.assertEqual(metrics["corpus_negative_refusals"], 1)
        self.assertEqual(metrics["corpus_negative_attempts"], 1)

    def test_empty_runs_directory_has_available_false(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = generate_payload(Path(directory), max_runs=5)

            self.assertFalse(payload["available"])
            self.assertIsNone(payload["selected_run_id"])


if __name__ == "__main__":
    unittest.main()
