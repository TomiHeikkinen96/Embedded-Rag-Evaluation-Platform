from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from generation.prompt_builder import (  # noqa: E402
    REFUSAL_TEXT,
    build_closed_book_messages,
    build_grounded_messages,
    referenced_source_labels,
    sources_from_retrieval,
)


class GroundedPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.results = [
            {
                "row": {
                    "title": "ESP32 Technical Reference Manual",
                    "source_path": "data/esp32_trm.pdf",
                    "page_number": 183,
                    "chunk_text": "The maximum output current is 40 mA.",
                    "paragraph_text": "The regulator maximum output current is 40 mA.",
                },
                "semantic_score": 0.8,
                "rerank_score": 0.9,
            }
        ]

    def test_retrieval_results_receive_stable_source_labels(self) -> None:
        sources = sources_from_retrieval(self.results)

        self.assertEqual(sources[0].label, "S1")
        self.assertEqual(sources[0].page_number, 183)
        self.assertIn("40 mA", sources[0].text)

    def test_prompt_requires_grounding_citations_and_refusal(self) -> None:
        messages = build_grounded_messages(
            "What is the maximum output current?",
            sources_from_retrieval(self.results),
        )

        self.assertEqual([message["role"] for message in messages], ["system", "user"])
        self.assertIn(REFUSAL_TEXT, messages[0]["content"])
        self.assertIn("[S1]", messages[1]["content"])
        self.assertIn("PDF page 183", messages[1]["content"])

    def test_citation_labels_are_ordered_and_deduplicated(self) -> None:
        labels = referenced_source_labels("First [S2], then [S1], and [S2] again.")

        self.assertEqual(labels, ["S2", "S1"])

    def test_closed_book_prompt_does_not_claim_sources_exist(self) -> None:
        messages = build_closed_book_messages("What is the value?")

        self.assertIn("No reference documents", messages[0]["content"])
        self.assertNotIn("[S1]", messages[0]["content"])
        self.assertEqual(messages[1]["content"], "What is the value?")


if __name__ == "__main__":
    unittest.main()
