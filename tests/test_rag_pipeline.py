import json
from pathlib import Path
import unittest

from rag.answer_generation import EvidenceItem, answer_with_model, evidence_from_results, validate_answer
from rag.query_router import RoutedRetriever

ROOT = Path(__file__).resolve().parents[1]
CARDS = json.loads((ROOT / "examples" / "sample_cards.json").read_text(encoding="utf-8"))


class PublicRAGPipelineTests(unittest.TestCase):
    def test_risk_query_retrieves_risk_evidence(self) -> None:
        retriever = RoutedRetriever(CARDS)
        _plan, results = retriever.search("What are the main risks with this stock?", top_k=3)
        self.assertEqual("EVIDENCE-003", results[0]["card"]["card_id"])

    def test_explicit_date_limits_candidate_scope(self) -> None:
        retriever = RoutedRetriever(CARDS)
        plan, results = retriever.search("What happened on 2026-01-21?", top_k=10)
        self.assertEqual(("2026-01-21",), plan.resolved_dates)
        self.assertTrue(results)
        self.assertTrue(all(item["card"].get("date") == "2026-01-21" for item in results))

    def test_grounded_answer_rejects_unknown_citation(self) -> None:
        evidence = [EvidenceItem("E1", "Example", "Supported fact.", "synthetic")]
        with self.assertRaises(ValueError):
            validate_answer(
                {
                    "support_status": "supported",
                    "answer": "A supported answer.",
                    "cited_evidence_ids": ["NOT_PROVIDED"],
                    "limitations": [],
                },
                evidence,
            )

    def test_invalid_model_output_falls_back_to_retrieved_evidence(self) -> None:
        retriever = RoutedRetriever(CARDS)
        _plan, results = retriever.search("Is this stock attractive?", top_k=2)
        evidence = evidence_from_results(results)

        answer = answer_with_model("Is this stock attractive?", evidence, lambda _prompt: "not json")
        self.assertEqual("partial", answer["support_status"])
        self.assertTrue(answer["cited_evidence_ids"])


if __name__ == "__main__":
    unittest.main()
