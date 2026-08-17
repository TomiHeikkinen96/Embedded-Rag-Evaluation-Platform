from __future__ import annotations

import re
import unicodedata

from evaluation.benchmark import GenerationCase
from generation.prompt_builder import REFUSAL_TEXT, referenced_source_labels


REFUSAL_INTENT_PATTERNS = (
    re.compile(r"\bi do not know\b", re.IGNORECASE),
    re.compile(r"\bi don't know\b", re.IGNORECASE),
    re.compile(r"\bcannot (?:answer|determine)\b", re.IGNORECASE),
    re.compile(r"\bnot (?:available|provided|supported) in (?:the )?(?:sources|documents|context)\b", re.IGNORECASE),
)


def normalize_answer(value: str) -> str:
    value = value.casefold().replace("µ", "u").replace("μ", "u").replace("×", "x")
    value = unicodedata.normalize("NFKD", value)
    return re.sub(r"[^a-z0-9]+", "", value)


def has_refusal_intent(answer: str) -> bool:
    return any(pattern.search(answer) for pattern in REFUSAL_INTENT_PATTERNS)


def score_answer(
    case: GenerationCase,
    answer: str,
    *,
    condition: str,
    available_source_labels: set[str],
) -> dict:
    normalized = normalize_answer(answer)
    fact_results = []
    for fact in case.required_facts:
        matched_variant = next(
            (
                variant
                for variant in fact["accepted"]
                if normalize_answer(variant) in normalized
            ),
            None,
        )
        fact_results.append(
            {
                "name": fact["name"],
                "matched": matched_variant is not None,
                "matched_variant": matched_variant,
            }
        )

    refusal_intent = has_refusal_intent(answer)
    exact_refusal = answer.strip() == REFUSAL_TEXT
    if case.answerability == "answerable":
        answer_correct = bool(fact_results) and all(
            result["matched"] for result in fact_results
        ) and not refusal_intent
    else:
        answer_correct = refusal_intent

    cited_labels = referenced_source_labels(answer)
    invalid_labels = [
        label for label in cited_labels if label not in available_source_labels
    ]
    grounded_condition = condition != "closed_book"
    citation_required = (
        grounded_condition
        and case.answerability == "answerable"
        and not refusal_intent
    )
    citations_valid = (
        not invalid_labels and (bool(cited_labels) if citation_required else True)
    )

    return {
        "answer_correct": answer_correct,
        "passed": answer_correct and citations_valid,
        "fact_results": fact_results,
        "refusal_intent": refusal_intent,
        "exact_refusal": exact_refusal,
        "citation_required": citation_required,
        "cited_labels": cited_labels,
        "invalid_citation_labels": invalid_labels,
        "citations_valid": citations_valid,
    }
