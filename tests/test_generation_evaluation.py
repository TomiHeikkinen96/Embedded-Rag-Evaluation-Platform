from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from evaluation.artifacts import summarize_results  # noqa: E402
from evaluation.benchmark import GenerationCase, load_benchmark  # noqa: E402
from evaluation.scoring import normalize_answer, score_answer  # noqa: E402


class GenerationEvaluationTests(unittest.TestCase):
    def test_committed_benchmark_is_valid(self) -> None:
        spec, cases = load_benchmark(
            PROJECT_ROOT / "benchmarks" / "esp32-generation-v1"
        )

        self.assertEqual(spec.conditions, ["closed_book", "oracle", "dense_rag:arctic"])
        self.assertGreaterEqual(len(cases), 6)

    def test_value_normalization_handles_units_and_symbols(self) -> None:
        self.assertEqual(normalize_answer("10 µA"), normalize_answer("10 uA"))
        self.assertEqual(normalize_answer("1024 × 8-bit"), normalize_answer("1024 x 8 bit"))

    def test_answerable_grounded_result_requires_facts_and_citation(self) -> None:
        case = GenerationCase(
            case_id="regulator",
            question="value?",
            task_type="exact_value",
            answerability="answerable",
            required_facts=[{"name": "current", "accepted": ["40 mA"]}],
            oracle_sources=[],
        )

        score = score_answer(
            case,
            "The maximum is 40 mA [S1].",
            condition="oracle",
            available_source_labels={"S1"},
        )

        self.assertTrue(score["answer_correct"])
        self.assertTrue(score["citations_valid"])
        self.assertTrue(score["passed"])

    def test_refusal_intent_and_exact_format_are_separate(self) -> None:
        case = GenerationCase(
            case_id="unknown",
            question="unknown?",
            task_type="unanswerable",
            answerability="unanswerable",
            required_facts=[],
            oracle_sources=[],
        )
        score = score_answer(
            case,
            "I do not know based on the provided documents. More text.",
            condition="oracle",
            available_source_labels=set(),
        )

        self.assertTrue(score["refusal_intent"])
        self.assertFalse(score["exact_refusal"])
        self.assertTrue(score["passed"])

    def test_recorded_oracle_phrasings_match_expected_facts(self) -> None:
        _, cases = load_benchmark(
            PROJECT_ROOT / "benchmarks" / "esp32-generation-v1"
        )
        cases_by_id = {case.case_id: case for case in cases}
        examples = {
            "input-only-gpio-limitations": (
                "GPIO pins 34-39 are input-only [S1]. These pins lack an output "
                "driver and internal pull-up/pull-down circuitry [S1]."
            ),
            "uart-controller-count-and-shared-ram": (
                "The ESP32 provides three UART controllers. Their FIFOs share "
                "1024 × 8-bit of RAM [S1]."
            ),
        }

        for case_id, answer in examples.items():
            with self.subTest(case_id=case_id):
                score = score_answer(
                    cases_by_id[case_id],
                    answer,
                    condition="oracle",
                    available_source_labels={"S1"},
                )
                self.assertTrue(score["passed"])

    def test_summary_groups_conditions(self) -> None:
        record = {
            "status": "completed",
            "condition": "oracle",
            "answerability": "answerable",
            "retrieval_evidence_hit": None,
            "score": {
                "passed": True,
                "answer_correct": True,
                "citations_valid": True,
                "refusal_intent": False,
                "exact_refusal": False,
                "citation_required": True,
            },
            "timing": {"context_seconds": 0.1, "generation_seconds": 1.0},
            "usage": {"prompt_tokens": 10, "output_tokens": 5},
        }

        summary = summarize_results([record])

        self.assertEqual(summary["conditions"]["oracle"]["pass_rate"], 1.0)
        self.assertEqual(summary["conditions"]["oracle"]["total_prompt_tokens"], 10)


if __name__ == "__main__":
    unittest.main()
