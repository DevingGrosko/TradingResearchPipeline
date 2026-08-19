# Synthetic RAG Example

This folder uses synthetic content only. It is intended to make the public retrieval flow inspectable without exposing private community data.

## Question

> What are the main reasons for and against this stock idea on January 21?

## Flow

```text
User question
    ↓
Deterministic date scope (2026-01-21)
    ↓
Raw-query BM25 + rewritten-query BM25
    ↓
Score fusion + soft card-type preference
    ↓
Small evidence bundle
    ↓
LLM receives question + evidence only
    ↓
Structured answer validated against supplied evidence IDs
```

The production system contains additional corpus validation, provenance rules, query planning, evaluation, and fallback behavior. This public subset is intentionally small enough to review quickly.
