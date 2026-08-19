from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Iterable

from .bm25 import BM25Index

_ISO_DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4, "may": 5,
    "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_NAMED_DATE_RE = re.compile(
    r"\b(" + "|".join(_MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(20\d{2}))?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class QueryPlan:
    original_query: str
    normalized_query: str
    expansion_terms: tuple[str, ...]
    preferred_card_types: tuple[str, ...]
    resolved_dates: tuple[str, ...]

    @property
    def rewritten_query(self) -> str:
        return " ".join((self.normalized_query, *self.expansion_terms)).strip()


def _available_dates(cards: Iterable[dict[str, Any]]) -> set[str]:
    return {str(card["date"]) for card in cards if card.get("date")}


def _resolve_dates(query: str, cards: list[dict[str, Any]]) -> tuple[str, ...]:
    available = _available_dates(cards)
    found: list[str] = []

    for year, month, day in _ISO_DATE_RE.findall(query):
        try:
            value = date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            continue
        if value in available and value not in found:
            found.append(value)

    for month_name, day, year in _NAMED_DATE_RE.findall(query):
        if not year:
            candidates = sorted(
                value for value in available
                if int(value[5:7]) == _MONTHS[month_name.lower()] and int(value[8:10]) == int(day)
            )
            if len(candidates) == 1 and candidates[0] not in found:
                found.append(candidates[0])
            continue
        try:
            value = date(int(year), _MONTHS[month_name.lower()], int(day)).isoformat()
        except ValueError:
            continue
        if value in available and value not in found:
            found.append(value)

    return tuple(found)


def route_query(query: str, cards: list[dict[str, Any]]) -> QueryPlan:
    """
    Produce a small public query plan.

    The production system can use an LLM semantic planner, but objective scope such as
    an explicit corpus date is resolved deterministically before retrieval.
    """
    normalized = " ".join(query.strip().split())
    lowered = normalized.lower()

    expansion: list[str] = []
    preferred: list[str] = []

    if any(word in lowered for word in ("risk", "wrong", "downside", "danger")):
        expansion += ["risk", "warning", "invalid"]
        preferred += ["evidence", "episode"]
    if any(word in lowered for word in ("why", "reason", "because")):
        expansion += ["reason", "decision", "context"]
        preferred += ["episode", "evidence"]
    if any(word in lowered for word in ("result", "outcome", "profit", "loss", "points")):
        expansion += ["outcome", "result"]
        preferred += ["outcome", "trade"]
    if any(word in lowered for word in ("overview", "what happened", "summary")):
        expansion += ["overview", "session"]
        preferred += ["day", "episode"]

    expansion_terms = tuple(dict.fromkeys(expansion))
    preferred_types = tuple(dict.fromkeys(preferred))

    return QueryPlan(
        original_query=query,
        normalized_query=normalized,
        expansion_terms=expansion_terms,
        preferred_card_types=preferred_types,
        resolved_dates=_resolve_dates(normalized, cards),
    )


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    maximum = max(values)
    if maximum <= 0:
        return [0.0 for _ in values]
    return [value / maximum for value in values]


class RoutedRetriever:
    """
    Date-scope first, then fuse raw-query and rewritten-query BM25 scores.

    This mirrors the main production idea while omitting private corpus rules and
    additional validation/evaluation layers.
    """

    def __init__(self, cards: Iterable[dict[str, Any]]) -> None:
        self.cards = list(cards)
        if not self.cards:
            raise ValueError("RoutedRetriever requires at least one card")

    def search(self, query: str, *, top_k: int = 5) -> tuple[QueryPlan, list[dict[str, Any]]]:
        plan = route_query(query, self.cards)
        candidates = self.cards
        if plan.resolved_dates:
            allowed = set(plan.resolved_dates)
            candidates = [card for card in candidates if card.get("date") in allowed]

        index = BM25Index(candidates)
        raw = index.search(plan.original_query)
        rewritten = index.search(plan.rewritten_query)

        raw_by_id = {result.card["card_id"]: result.score for result in raw}
        rewritten_by_id = {result.card["card_id"]: result.score for result in rewritten}
        ids = [card["card_id"] for card in candidates]

        raw_norm = dict(zip(ids, _normalize([raw_by_id.get(card_id, 0.0) for card_id in ids])))
        rewritten_norm = dict(
            zip(ids, _normalize([rewritten_by_id.get(card_id, 0.0) for card_id in ids]))
        )

        ranked: list[dict[str, Any]] = []
        for card in candidates:
            card_id = card["card_id"]
            score = raw_norm[card_id] + 0.65 * rewritten_norm[card_id]
            if card.get("card_type") in plan.preferred_card_types:
                score += 0.08
            ranked.append({"score": score, "card": card})

        ranked.sort(key=lambda item: (-item["score"], item["card"]["card_id"]))
        return plan, ranked[: max(top_k, 0)]
