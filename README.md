# Trading Research & Modeling Pipeline

Python research pipeline for turning trading commentary, video transcripts, chart screenshots, and OHLCV futures data into structured research datasets for later modeling.

The goal of this repository is to show the code and architecture without publishing private source data, Discord exports, screenshots, market-data files, or generated archives.

## What It Contains

- `discord_archive/`: Discord message archiving utilities that export message metadata, text, attachments, and provenance into JSONL/Markdown formats.
- `video_pipeline/`: Caption-first video tooling for parsing VTT/SRT transcripts, extracting chart frames, and building AI-ready context files that align transcript segments with nearby screenshots.
- `market_structure/`: pandas-based OHLCV utilities for futures contract processing, timeframe aggregation, swing-point checks, SMT-style divergence checks, and trend/regime classification.
- `docs/`: schema and planning docs for building structured trading research episodes and belief-state timelines.

## Tech Stack

- Python
- pandas, NumPy, SciPy
- SQL/data pipeline concepts
- Databento DBN processing
- Discord API
- PyAV and Pillow for video/image processing
- JSONL and Markdown research artifacts

## Data Policy

This public version intentionally excludes:

- Discord exports and message archives
- Video files, screenshots, and transcript archives
- OHLCV CSV/DBN market data
- API tokens and `.env` files
- Generated research casebooks

The code expects those assets to exist locally when running the full pipeline.

## Project Direction

The long-term goal is to build a dataset that can support:

- source-backed trading episode reconstruction
- similar-episode retrieval
- time-series outcome analysis
- model-ready feature generation
- candidate trading-rule/hypothesis generation

This is a research/data engineering project, not a production trading system.
