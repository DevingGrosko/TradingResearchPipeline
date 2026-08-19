from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Iterable

SUPPORTED_STATUSES = {"supported", "partial", "unsupported"}


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    title: str
    text: str
    source: str


def evidence_from_results(results: Iterable[dict[str, Any]], *, limit: int = 5) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for result in list(results)[:limit]:
        card = result["card"]
        items.append(
            EvidenceItem(
                evidence_id=str(card["card_id"]),
                title=str(card.get("title", "Untitled evidence")),
                text=str(card.get("text", "")),
                source=str(card.get("source", "archive")),
            )
        )
    return items


def build_grounded_prompt(question: str, evidence: Iterable[EvidenceItem]) -> str:
    """Build a bounded prompt containing only the evidence selected for this answer."""
    evidence = list(evidence)
    blocks = [
        "Answer the user's question using only the evidence below.",
        "Do not add facts that are not supported by the supplied evidence.",
        "Return JSON with: support_status, answer, cited_evidence_ids, limitations.",
        "support_status must be supported, partial, or unsupported.",
        "",
        f"QUESTION: {question}",
        "",
        "EVIDENCE:",
    ]
    for item in evidence:
        blocks.append(
            f"[{item.evidence_id}] {item.title}\nSource: {item.source}\n{item.text}"
        )
    return "\n\n".join(blocks)


def _coerce_payload(value: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Model output must be a JSON object")


def validate_answer(payload: dict[str, Any], evidence: Iterable[EvidenceItem]) -> dict[str, Any]:
    """Reject unsupported citations and structurally invalid grounded answers."""
    allowed_ids = {item.evidence_id for item in evidence}
    status = payload.get("support_status")
    answer = payload.get("answer")
    cited = payload.get("cited_evidence_ids", [])
    limitations = payload.get("limitations", [])

    if status not in SUPPORTED_STATUSES:
        raise ValueError(f"Invalid support_status: {status!r}")
    if not isinstance(answer, str):
        raise ValueError("answer must be a string")
    if not isinstance(cited, list) or not all(isinstance(item, str) for item in cited):
        raise ValueError("cited_evidence_ids must be a list of strings")
    if not isinstance(limitations, list) or not all(isinstance(item, str) for item in limitations):
        raise ValueError("limitations must be a list of strings")

    unknown = set(cited) - allowed_ids
    if unknown:
        raise ValueError(f"Answer cited evidence that was not supplied: {sorted(unknown)}")
    if status == "unsupported" and cited:
        raise ValueError("unsupported answers cannot cite evidence as supporting a factual answer")
    if status in {"supported", "partial"} and not answer.strip():
        raise ValueError("supported/partial answers need answer text")

    return {
        "support_status": status,
        "answer": answer.strip(),
        "cited_evidence_ids": cited,
        "limitations": limitations,
    }


def extractive_fallback(evidence: Iterable[EvidenceItem]) -> dict[str, Any]:
    """Fail safely by surfacing retrieved material instead of inventing an answer."""
    evidence = list(evidence)
    if not evidence:
        return {
            "support_status": "unsupported",
            "answer": "I could not find enough supporting material in the archive to answer this.",
            "cited_evidence_ids": [],
            "limitations": ["No evidence was retrieved."],
        }

    preview = " ".join(item.text.strip() for item in evidence[:2] if item.text.strip())
    return {
        "support_status": "partial",
        "answer": preview or "Relevant evidence was found, but answer generation was unavailable.",
        "cited_evidence_ids": [item.evidence_id for item in evidence[:2]],
        "limitations": ["Returned an extractive fallback because model output was unavailable or invalid."],
    }


def answer_with_model(
    question: str,
    evidence: Iterable[EvidenceItem],
    model_call: Callable[[str], dict[str, Any] | str],
) -> dict[str, Any]:
    """
    Generate a grounded answer with a caller-supplied LLM function.

    The public code intentionally leaves provider credentials/transport outside this module.
    """
    evidence = list(evidence)
    prompt = build_grounded_prompt(question, evidence)
    try:
        payload = _coerce_payload(model_call(prompt))
        return validate_answer(payload, evidence)
    except (ValueError, TypeError, json.JSONDecodeError):
        return extractive_fallback(evidence)
