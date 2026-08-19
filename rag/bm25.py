from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import re
from typing import Any, Iterable

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Deterministic tokenizer used by the lexical retriever."""
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text or "")]


def card_text(card: dict[str, Any]) -> str:
    """Keep retrieval text explicit and inspectable."""
    return f"{card.get('title', '')}\n{card.get('text', '')}".strip()


@dataclass(frozen=True)
class SearchResult:
    rank: int
    score: float
    card: dict[str, Any]


class BM25Index:
    """Small transparent Okapi BM25 implementation used for public demos/tests."""

    def __init__(
        self,
        cards: Iterable[dict[str, Any]],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be greater than zero")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")

        self.cards = list(cards)
        if not self.cards:
            raise ValueError("BM25Index requires at least one card")

        ids = [card.get("card_id") for card in self.cards]
        if any(not isinstance(card_id, str) or not card_id for card_id in ids):
            raise ValueError("Every card needs a non-empty card_id")
        if len(ids) != len(set(ids)):
            raise ValueError("card_id values must be unique")

        self.k1 = float(k1)
        self.b = float(b)
        self._term_frequencies: list[Counter[str]] = []
        self._document_lengths: list[int] = []
        document_frequency: Counter[str] = Counter()

        for card in self.cards:
            tokens = tokenize(card_text(card))
            frequencies = Counter(tokens)
            self._term_frequencies.append(frequencies)
            self._document_lengths.append(len(tokens))
            document_frequency.update(frequencies.keys())

        self.document_count = len(self.cards)
        self.average_document_length = sum(self._document_lengths) / self.document_count
        self._idf = {
            term: math.log(1.0 + (self.document_count - df + 0.5) / (df + 0.5))
            for term, df in document_frequency.items()
        }

    def search(self, query: str, *, top_k: int | None = None) -> list[SearchResult]:
        query_frequencies = Counter(tokenize(query))
        scored: list[tuple[float, str, dict[str, Any]]] = []

        for index, card in enumerate(self.cards):
            length = self._document_lengths[index]
            norm = 1.0 - self.b + self.b * length / self.average_document_length
            frequencies = self._term_frequencies[index]
            score = 0.0

            for term, query_count in query_frequencies.items():
                tf = frequencies.get(term, 0)
                if not tf:
                    continue
                denominator = tf + self.k1 * norm
                score += (
                    self._idf.get(term, 0.0)
                    * (tf * (self.k1 + 1.0) / denominator)
                    * query_count
                )

            scored.append((score, str(card["card_id"]), card))

        # Deterministic tie-break keeps tests and evaluation reproducible.
        scored.sort(key=lambda item: (-item[0], item[1]))
        if top_k is not None:
            scored = scored[: max(top_k, 0)]

        return [
            SearchResult(rank=rank, score=score, card=card)
            for rank, (score, _card_id, card) in enumerate(scored, start=1)
        ]
