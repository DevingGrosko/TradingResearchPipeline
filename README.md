# Trading Research & RAG Pipeline

Python research and retrieval pipeline for turning trading commentary, video transcripts, screenshots, reviews, and market data into structured evidence that can be searched and used to generate grounded AI answers.

This public repository shows the architecture and a sanitized subset of the RAG implementation without publishing private community data, Discord exports, screenshots, generated corpus records, or credentials.

## RAG Flow

```text
Raw archive
    ↓
Structured records
    ↓
Query planning + deterministic scope
    ↓
Raw BM25 + rewritten BM25 retrieval
    ↓
Score fusion + evidence selection
    ↓
LLM receives question + bounded evidence
    ↓
Grounded answer validation
```

The production system contains additional corpus validation, provenance rules, semantic planning, evaluation, and regression infrastructure. The `rag/` folder is intentionally small enough to review quickly while still showing the core retrieval and grounding ideas.

## Public RAG Subset

- `rag/bm25.py`: transparent Okapi BM25 implementation over structured cards.
- `rag/query_router.py`: query normalization, deterministic date scoping, query expansion, raw/rewritten retrieval, and score fusion.
- `rag/answer_generation.py`: bounded evidence prompts, structured support states, citation validation, and extractive fallback behavior.
- `tests/test_rag_pipeline.py`: representative tests for retrieval, date isolation, citation grounding, and fallback behavior.
- `examples/sample_cards.json`: synthetic records used by the public demo/tests.
- `examples/example_query.md`: a simple end-to-end walkthrough.

Run the public RAG tests with:

```bash
python -m unittest discover -s tests -v
```

## Other Pipeline Components

- `discord_archive/`: Discord message archiving utilities that preserve message text, metadata, attachments, and provenance.
- `video_pipeline/`: transcript and video tooling for extracting context, processing captions, and aligning text with nearby frames/screenshots.
- `market_structure/`: pandas-based OHLCV utilities for futures contract processing, timeframe aggregation, swing-point checks, SMT-style divergence checks, and trend/regime classification.

## Tech Stack

- Python
- RAG / LLM workflows
- BM25 retrieval and query rewriting
- Structured outputs and evidence grounding
- pandas, NumPy, SciPy
- Databento DBN processing
- Discord API
- PyAV and Pillow
- JSON / JSONL research artifacts

## Data Policy

This public version intentionally excludes:

- Discord exports and message archives
- Video files, screenshots, and transcript archives
- OHLCV CSV/DBN market data
- API tokens and `.env` files
- Generated private corpus records
- Private community/educator content

The synthetic files under `examples/` are safe stand-ins for the private corpus.

## Project Goal

The broader system is designed to support source-backed episode reconstruction, retrieval over a large trading archive, question answering grounded in retrieved evidence, cross-day research, and later model/evaluation work.

This repository is a public technical showcase of that system rather than a standalone production trading application.
