from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ARCHIVE_ROOT = Path("archive")
COMPLETE_STATUS = "ai_contextual_cc_cleanup_complete"


@dataclass(frozen=True)
class Segment:
    index: int
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Pattern:
    id: str
    category: str
    regex: str
    reason: str
    examples: str
    score: int


@dataclass
class WorkItemStatus:
    path: str
    name: str
    main_json: str
    transcript: str
    review: str
    needs_review: str
    stale_ai_context: list[str]
    cleanup_status: str
    segments: int
    duration: float | None
    classification: str
    reasons: list[str]


@dataclass
class Candidate:
    item: str
    item_path: str
    source_json: str
    transcript: str
    segment_index: int
    timestamp: str
    category: str
    pattern_id: str
    score: int
    matched: str
    reason: str
    examples: str
    context: list[str]
    screenshots: list[str]


PATTERNS = [
    Pattern(
        "smt_damage",
        "SMT / SSMT",
        r"\b(?:some tea|some T\b|sum tea|sub T\b|sconch\w*|sconcho|ostentee|squash\w*|crunch\w*|sequential certainty|control some|show some|social something|exponential sum)\b",
        "SMT/SSMT language is commonly damaged by captions.",
        "`some tea` -> `SMT`; `sconcho sconty` -> `sequential SMT`",
        95,
    ),
    Pattern(
        "ticker_damage",
        "Ticker",
        r"\b(?:and Q|in Q|an Q|thank you|wine|why am|Phil Sue|fill Sue|NQVS|NQBS)\b",
        "Ticker symbols often become normal English words.",
        "`and Q` -> `NQ`; `wine` -> `YM`; `Phil Sue` -> `fails to` in index-comparison context",
        95,
    ),
    Pattern(
        "draw_liquidity_damage",
        "Draw On Liquidity",
        r"\b(?:drawn? (?:equity|quality|liquidity)|draws? on (?:the )?(?:hoodity|coodity|community|quote|quality)|Jean Aquatic|John liquidity|John the quality|general quantity|job liquidity|jaws on)\b",
        "Draw-on-liquidity phrases can look grammatical while being wrong.",
        "`draw on the quality` -> `draw on liquidity`",
        95,
    ),
    Pattern(
        "timeframe_damage",
        "Timeframe",
        r"\b(?:50[- ]minute|9[- ]minute|9%|fireman chart|fora fractal|four a fractal|famine|farm|family|finite time frame|woman)\b",
        "Timeframe words are repeatedly misheard and can invert the setup logic.",
        "`50-minute` often -> `15-minute`; `woman` often -> `one-minute`",
        90,
    ),
    Pattern(
        "market_maker_po3_damage",
        "Market Maker / PO3",
        r"\b(?:Markle Maker|mark maker|mark make|market make\b|bar three|power through|Power3|Power 3|cell side|bison|bar side)\b",
        "PO3/MMxM wording often gets turned into ordinary words.",
        "`bar three` -> `Power of Three`; `cell side` -> `sellside`",
        90,
    ),
    Pattern(
        "htf_ltf_damage",
        "HTF / LTF",
        r"\b(?:hard time(?: frame| from)?|high time for|time for impudry|lower time from|half time frame)\b",
        "HTF/LTF and PDA context is often damaged.",
        "`hard time frame` -> `higher-timeframe`; `time for impudry` -> `timeframe PDA`",
        85,
    ),
    Pattern(
        "cisd_damage",
        "CISD",
        r"\b(?:C\.?I\.?Z\.?D?|CIZ|C I Z|CIs Dean|Sea eyes|series D|moment CID|idsd|sysd|cagd|cagm|crsd)\b",
        "CISD captions are frequently mangled.",
        "`CIs Dean` -> `CISD`",
        85,
    ),
    Pattern(
        "true_open_gap_damage",
        "True Open / Gap",
        r"\b(?:tree open|two (?:day|week|month|session) open|too (?:day|week|month|session) open|new log|new dogs?|new world gap)\b",
        "True opens and NWOG/NDOG can become normal words.",
        "`two day open` -> `true day open`; `new dog` -> `NDOG`",
        80,
    ),
    Pattern(
        "previous_level_damage",
        "Previous Level",
        r"\b(?:pre-say|pre-spy|pre-sm\w+|pure says|free-speed|previous say|low today|high today|hide the week|high, the week)\b",
        "Previous day/week/month and previous candle levels often need context.",
        "`pre-say high` -> `previous day high`; `pre-spy-minute low` -> `previous 5-minute low`",
        80,
    ),
    Pattern(
        "risk_trade_damage",
        "Risk / Trade",
        r"\b(?:risk award|battery reward|TP month|Souplas|D stop us|ATB|too many|my life\b|fundage|Last second trade)\b",
        "Trade-management captions can alter meaning.",
        "`risk award` -> `risk/reward`; `Souplas` -> `stop loss`; `too many` -> `two minis`",
        75,
    ),
    Pattern(
        "ordinary_context_trap",
        "Ordinary Word Trap",
        r"\b(?:mentors|universal|not stupid|go to everyone|daily mark review|display are displaced|chart my phone|the quality|climate structure|bush distribution|priest for high)\b",
        "Ordinary-looking words have repeatedly been wrong in this domain.",
        "`mentors` may be `fundamentals`; `priest for high` may be `previous four-hour high`",
        70,
    ),
]


def parse_time(value: str) -> float:
    value = value.strip()
    parts = value.split(":")
    if len(parts) == 1:
        minutes, seconds, millis = re.match(r"^(\d+)\.(\d+)\.(\d+)$", value).groups()
        return int(minutes) * 60 + int(seconds) + int(millis) / 1000
    if len(parts) == 2:
        minutes, rest = parts
        seconds, millis = rest.split(".")
        return int(minutes) * 60 + int(seconds) + int(millis) / 1000
    if len(parts) == 3:
        hours, minutes, rest = parts
        seconds, millis = rest.split(".")
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000
    raise ValueError(f"Cannot parse timestamp: {value}")


def fmt_time(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    sec = total_seconds % 60
    minute = (total_seconds // 60) % 60
    hour = total_seconds // 3600
    if hour:
        return f"{hour:02d}:{minute:02d}:{sec:02d}.{ms:03d}"
    return f"{minute:02d}.{sec:02d}.{ms:03d}"


def segment_line(segment: Segment) -> str:
    return f"[{fmt_time(segment.start)}-{fmt_time(segment.end)}] {segment.text}"


def find_item_dirs(root: Path) -> list[Path]:
    if (root / "json").is_dir() or list(root.glob("*.txt")):
        return [root]
    return sorted([path for path in root.iterdir() if path.is_dir()])


def main_json_for(item: Path) -> Path | None:
    json_dir = item / "json"
    if not json_dir.exists():
        return None
    candidates = [path for path in sorted(json_dir.glob("*.json")) if not path.name.endswith("_ai_context.json")]
    return candidates[0] if candidates else None


def transcript_for(item: Path) -> Path | None:
    candidates = sorted(item.glob("*.txt"))
    return candidates[0] if candidates else None


def review_for(item: Path) -> Path | None:
    candidates = sorted(item.glob("*_review.md"))
    return candidates[0] if candidates else None


def needs_review_for(item: Path) -> Path | None:
    candidates = sorted(item.glob("*_needs_review.md"))
    return candidates[0] if candidates else None


def load_json(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"_json_error": True}


def normalize_frame_path(item: Path, value: Any) -> str:
    if not value:
        return ""
    original = str(value)
    path = Path(original)
    if path.exists():
        return original

    image_root = item / "images"
    if "images" in path.parts:
        rel = Path(*path.parts[path.parts.index("images") + 1 :])
        candidate = image_root / rel
        if candidate.exists():
            return str(candidate)

    if path.name and image_root.exists():
        matches = sorted(image_root.glob(f"**/{path.name}"))
        if matches:
            return str(matches[0])
    return original


def classify_item(item: Path) -> WorkItemStatus:
    main_json = main_json_for(item)
    transcript = transcript_for(item)
    review = review_for(item)
    needs_review = needs_review_for(item)
    stale = sorted((item / "json").glob("*_ai_context.json")) if (item / "json").exists() else []
    data = load_json(main_json)
    cleanup = data.get("cleanup") if isinstance(data.get("cleanup"), dict) else {}
    cleanup_status = str(cleanup.get("status") or "")
    segments = len(data.get("segments", [])) if isinstance(data.get("segments"), list) else 0
    duration = data.get("duration") if isinstance(data.get("duration"), (int, float)) else None

    reasons: list[str] = []
    if not main_json:
        reasons.append("missing main JSON")
    if not transcript:
        reasons.append("missing transcript txt")
    if stale:
        reasons.append("stale *_ai_context.json exists")
    if cleanup_status != COMPLETE_STATUS:
        reasons.append("main JSON cleanup.status is not complete")
    if needs_review and needs_review.stat().st_size > 0:
        reasons.append("needs_review file exists")
    if review:
        try:
            if "_ai_context.json" in review.read_text(encoding="utf-8", errors="ignore"):
                reasons.append("review still references AI-context JSON")
        except OSError:
            pass

    if not main_json or not transcript:
        classification = "missing"
    elif cleanup_status == COMPLETE_STATUS and not stale:
        classification = "complete_with_unresolved_review" if needs_review and needs_review.stat().st_size > 0 else "complete"
    elif cleanup_status or review or needs_review or stale:
        classification = "partial"
    else:
        classification = "raw"

    return WorkItemStatus(
        path=str(item),
        name=item.name,
        main_json=str(main_json) if main_json else "",
        transcript=str(transcript) if transcript else "",
        review=str(review) if review else "",
        needs_review=str(needs_review) if needs_review else "",
        stale_ai_context=[str(path) for path in stale],
        cleanup_status=cleanup_status,
        segments=segments,
        duration=float(duration) if duration is not None else None,
        classification=classification,
        reasons=reasons,
    )


def load_segments(item: Path) -> tuple[Path | None, Path | None, list[Segment]]:
    main_json = main_json_for(item)
    transcript = transcript_for(item)
    if main_json:
        data = load_json(main_json)
        raw = data.get("segments", [])
        if isinstance(raw, list) and raw:
            return main_json, transcript, [
                Segment(index=index, start=float(seg["start"]), end=float(seg["end"]), text=str(seg["text"]))
                for index, seg in enumerate(raw, 1)
            ]
    segments: list[Segment] = []
    if transcript:
        for index, line in enumerate(transcript.read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"^\[([^\]-]+)-([^\]]+)\]\s+(.*)$", line)
            if not match:
                continue
            segments.append(Segment(index=index, start=parse_time(match.group(1)), end=parse_time(match.group(2)), text=match.group(3)))
    return main_json, transcript, segments


def load_frames(item: Path, source_json: Path | None) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    if source_json:
        data = load_json(source_json)
        manifest = data.get("images", {}).get("manifest") if isinstance(data.get("images"), dict) else None
        if manifest and Path(manifest).exists():
            frames = list(json.loads(Path(manifest).read_text(encoding="utf-8")).get("frames", []))
    image_root = item / "images"
    if not frames:
        manifests = sorted(image_root.glob("*/manifest.json"))
        if manifests:
            frames = list(json.loads(manifests[0].read_text(encoding="utf-8")).get("frames", []))

    normalized = []
    for frame in frames:
        frame = dict(frame)
        raw_path = frame.get("path") or frame.get("file")
        normalized_path = normalize_frame_path(item, raw_path)
        if normalized_path:
            frame["path"] = normalized_path
        normalized.append(frame)
    return normalized


def nearest_screenshots(frames: list[dict[str, Any]], seconds: float, limit: int) -> list[str]:
    ranked = sorted(frames, key=lambda frame: abs(float(frame.get("time", 0.0)) - seconds))
    return [str(frame.get("path") or frame.get("file")) for frame in ranked[:limit] if frame.get("path") or frame.get("file")]


def scan_item(item: Path, context: int, screenshot_limit: int, max_candidates: int | None) -> list[Candidate]:
    source_json, transcript, segments = load_segments(item)
    frames = load_frames(item, source_json)
    compiled = [(pattern, re.compile(pattern.regex, re.IGNORECASE)) for pattern in PATTERNS]
    candidates: list[Candidate] = []

    for segment in segments:
        hits = []
        for pattern, regex in compiled:
            match = regex.search(segment.text)
            if match:
                hits.append((pattern, match.group(0)))
        if not hits:
            continue
        start = max(1, segment.index - context)
        end = min(len(segments), segment.index + context)
        context_lines = [segment_line(seg) for seg in segments[start - 1:end]]
        screenshots = nearest_screenshots(frames, (segment.start + segment.end) / 2, screenshot_limit)
        for pattern, matched in hits:
            candidates.append(
                Candidate(
                    item=item.name,
                    item_path=str(item),
                    source_json=str(source_json) if source_json else "",
                    transcript=str(transcript) if transcript else "",
                    segment_index=segment.index,
                    timestamp=f"{fmt_time(segment.start)}-{fmt_time(segment.end)}",
                    category=pattern.category,
                    pattern_id=pattern.id,
                    score=pattern.score,
                    matched=matched,
                    reason=pattern.reason,
                    examples=pattern.examples,
                    context=context_lines,
                    screenshots=screenshots,
                )
            )

    candidates.sort(key=lambda candidate: (-candidate.score, candidate.segment_index, candidate.pattern_id))
    if max_candidates is not None:
        candidates = candidates[:max_candidates]
    return candidates


def status_markdown(statuses: list[WorkItemStatus]) -> str:
    lines = [
        "# Transcript Cleanup Status",
        "",
        "| Item | Class | Cleanup | Stale AI | Needs Review | Segments | Reasons |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for status in statuses:
        lines.append(
            "| {name} | {classification} | {cleanup} | {stale} | {needs} | {segments} | {reasons} |".format(
                name=status.name.replace("|", "\\|"),
                classification=status.classification,
                cleanup=status.cleanup_status or "-",
                stale=len(status.stale_ai_context),
                needs="yes" if status.needs_review else "no",
                segments=status.segments,
                reasons="; ".join(status.reasons).replace("|", "\\|") or "-",
            )
        )
    return "\n".join(lines) + "\n"


def scan_markdown(item: Path, candidates: list[Candidate]) -> str:
    lines = [
        f"# Suspicious Transcript Context - {item.name}",
        "",
        f"Candidates: `{len(candidates)}`",
        "",
    ]
    for number, candidate in enumerate(candidates, 1):
        lines.extend(
            [
                f"## {number}. {candidate.timestamp} - {candidate.category}",
                "",
                f"- Pattern: `{candidate.pattern_id}`",
                f"- Matched: `{candidate.matched}`",
                f"- Reason: {candidate.reason}",
                f"- Examples: {candidate.examples}",
                f"- Segment: `{candidate.segment_index}`",
                "",
            ]
        )
        if candidate.screenshots:
            lines.append("Screenshots:")
            for screenshot in candidate.screenshots:
                lines.append(f"- `{screenshot}`")
            lines.append("")
        lines.extend(["```text", *candidate.context, "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def resolve_roots(args: argparse.Namespace) -> list[Path]:
    if args.path:
        return [Path(args.path)]
    if args.scope == "days":
        return [ARCHIVE_ROOT / "Days"]
    if args.scope == "concepts":
        return [ARCHIVE_ROOT / "Concepts" / "transcripts"]
    return [ARCHIVE_ROOT / "Days", ARCHIVE_ROOT / "Concepts" / "transcripts"]


def filter_items(items: list[Path], names: list[str]) -> list[Path]:
    if not names:
        return items
    wanted = set(names)
    return [item for item in items if item.name in wanted]


def write_outputs(out_dir: Path | None, name: str, content: str) -> None:
    if not out_dir:
        print(content)
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / name).write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage transcript cleanup status and suspicious caption context.")
    parser.add_argument("command", choices=["status", "scan"])
    parser.add_argument("--scope", choices=["days", "concepts", "all"], default="days")
    parser.add_argument("--path", help="Direct item/root path to inspect.")
    parser.add_argument("--item", action="append", default=[], help="Specific child item name/date. Repeatable.")
    parser.add_argument("--out-dir", type=Path, help="Write markdown/json reports here instead of stdout.")
    parser.add_argument("--context", type=int, default=3, help="Segments before/after each suspicious hit.")
    parser.add_argument("--screenshots", type=int, default=2, help="Nearest screenshots per suspicious hit.")
    parser.add_argument("--max-candidates", type=int, default=None)
    args = parser.parse_args()

    roots = resolve_roots(args)
    items: list[Path] = []
    for root in roots:
        items.extend(find_item_dirs(root))
    items = filter_items(sorted(items), args.item)

    if args.command == "status":
        statuses = [classify_item(item) for item in items]
        write_outputs(args.out_dir, "cleanup_status.md", status_markdown(statuses))
        if args.out_dir:
            (args.out_dir / "cleanup_status.json").write_text(json.dumps([asdict(status) for status in statuses], indent=2) + "\n", encoding="utf-8")
        return 0

    all_candidates: list[Candidate] = []
    for item in items:
        candidates = scan_item(item, args.context, args.screenshots, args.max_candidates)
        all_candidates.extend(candidates)
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", item.name).strip("_")
        write_outputs(args.out_dir, f"{safe_name}_suspicious_context.md", scan_markdown(item, candidates))
    if args.out_dir:
        (args.out_dir / "candidates.json").write_text(json.dumps([asdict(candidate) for candidate in all_candidates], indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
