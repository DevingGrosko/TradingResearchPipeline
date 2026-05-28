from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from pathlib import Path
from typing import Any, Iterable


def timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    seconds_part = total_seconds % 60
    minutes = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds_part:02d}.{ms:03d}"
    return f"{minutes:02d}.{seconds_part:02d}.{ms:03d}"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def relative_path(path: Path, start: Path) -> str:
    return path.resolve().relative_to(start.resolve()).as_posix()


def frame_ref(frame: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    path = Path(frame["path"])
    derivatives = []
    for derivative in frame.get("derivatives", []):
        derivative_path = Path(derivative["path"])
        derivatives.append(
            {
                **derivative,
                "relative_path": relative_path(derivative_path, output_dir),
            }
        )
    return {
        "time": frame["time"],
        "timestamp": frame["timestamp"],
        "file": frame["file"],
        "path": str(path),
        "relative_path": relative_path(path, output_dir),
        "width": frame.get("width"),
        "height": frame.get("height"),
        "source_width": frame.get("source_width"),
        "source_height": frame.get("source_height"),
        "reason": frame.get("reason", []),
        "scene_score": frame.get("scene_score"),
        "derivatives": derivatives,
    }


def nearest_frames(
    segment: dict[str, Any],
    frames: list[dict[str, Any]],
    frame_times: list[float],
    window_seconds: float,
    max_images: int,
) -> list[dict[str, Any]]:
    midpoint = (segment["start"] + segment["end"]) / 2
    in_window = [
        frame
        for frame in frames
        if segment["start"] - window_seconds <= frame["time"] <= segment["end"] + window_seconds
    ]
    candidates = in_window
    if not candidates:
        index = bisect_left(frame_times, midpoint)
        candidates = []
        for nearby_index in (index - 1, index, index + 1):
            if 0 <= nearby_index < len(frames):
                candidates.append(frames[nearby_index])
    return sorted(candidates, key=lambda frame: abs(frame["time"] - midpoint))[:max_images]


def build_blocks(
    segments: list[dict[str, Any]],
    frames: list[dict[str, Any]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        previous_time = frames[index - 1]["time"] if index > 0 else 0.0
        next_time = frames[index + 1]["time"] if index + 1 < len(frames) else None
        start_boundary = (previous_time + frame["time"]) / 2 if index > 0 else 0.0
        end_boundary = (frame["time"] + next_time) / 2 if next_time is not None else float("inf")
        block_segments = [
            segment
            for segment in segments
            if start_boundary <= (segment["start"] + segment["end"]) / 2 < end_boundary
        ]
        blocks.append(
            {
                "image": frame_ref(frame, output_dir),
                "start": round(start_boundary, 3),
                "end": None if end_boundary == float("inf") else round(end_boundary, 3),
                "segments": block_segments,
            }
        )
    return blocks


def write_markdown(
    markdown_path: Path,
    source_json_path: Path,
    ai_context_path: Path,
    source: dict[str, Any],
    blocks: list[dict[str, Any]],
    max_segments_per_block: int,
) -> None:
    output_dir = markdown_path.parent
    lines = [
        f"# {markdown_path.stem.replace('_review', '').replace('_', ' ')}",
        "",
        f"- Source kind: `{source.get('source_kind', 'unknown')}`",
        f"- Transcript JSON: `{relative_path(source_json_path, output_dir)}`",
        f"- AI context JSON: `{relative_path(ai_context_path, output_dir)}`",
        f"- Segments: `{len(source.get('segments', []))}`",
        f"- Images: `{source.get('images', {}).get('count', 0)}`",
        "",
    ]
    for block in blocks:
        image = block["image"]
        block_segments = block["segments"][:max_segments_per_block]
        if not block_segments:
            continue
        lines.extend(
            [
                f"## {image['timestamp']}",
                "",
                f"![{image['file']}]({image['relative_path']})",
                "",
            ]
        )
        for derivative in image.get("derivatives", []):
            lines.extend(
                [
                    f"**{derivative['role']}**",
                    "",
                    f"![{derivative['file']}]({derivative['relative_path']})",
                    "",
                ]
            )
        for segment in block_segments:
            lines.append(
                f"- `[{timestamp(segment['start'])}-{timestamp(segment['end'])}]` {segment['text']}"
            )
        if len(block["segments"]) > max_segments_per_block:
            lines.append(f"- ... {len(block['segments']) - max_segments_per_block} more segments")
        lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def build_context(
    source_json_path: Path,
    window_seconds: float,
    max_images: int,
    max_segments_per_block: int,
) -> tuple[Path, Path]:
    source = load_json(source_json_path)
    images = source.get("images")
    if not images or not images.get("manifest"):
        raise SystemExit(f"No image manifest found in {source_json_path}")
    image_manifest = load_json(Path(images["manifest"]))
    frames = sorted(image_manifest.get("frames", []), key=lambda frame: frame["time"])
    if not frames:
        raise SystemExit(f"No image frames found in {images['manifest']}")

    output_dir = source_json_path.parent.parent
    stem = source_json_path.stem
    frame_times = [frame["time"] for frame in frames]
    enriched_segments = []
    for segment in source.get("segments", []):
        nearby = nearest_frames(segment, frames, frame_times, window_seconds, max_images)
        enriched_segments.append(
            {
                **segment,
                "nearby_images": [frame_ref(frame, output_dir) for frame in nearby],
            }
        )
    blocks = build_blocks(source.get("segments", []), frames, output_dir)
    context = {
        "source": source.get("source"),
        "source_kind": source.get("source_kind"),
        "source_name": source.get("source_name"),
        "language": source.get("language"),
        "duration": source.get("duration"),
        "window_seconds": window_seconds,
        "max_images_per_segment": max_images,
        "segments": enriched_segments,
        "image_blocks": blocks,
    }
    ai_context_path = source_json_path.parent / f"{stem}_ai_context.json"
    markdown_path = output_dir / f"{stem}_review.md"
    ai_context_path.write_text(json.dumps(context, indent=2), encoding="utf-8")
    write_markdown(
        markdown_path=markdown_path,
        source_json_path=source_json_path,
        ai_context_path=ai_context_path,
        source=source,
        blocks=blocks,
        max_segments_per_block=max_segments_per_block,
    )
    return ai_context_path, markdown_path


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build AI-context JSON and human Markdown from transcript JSON plus images."
    )
    parser.add_argument("json_files", nargs="+", help="Transcript JSON files.")
    parser.add_argument("--window-seconds", type=float, default=20.0)
    parser.add_argument("--max-images", type=int, default=3)
    parser.add_argument("--max-segments-per-block", type=int, default=12)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    for raw_path in args.json_files:
        ai_context_path, markdown_path = build_context(
            source_json_path=Path(raw_path).expanduser(),
            window_seconds=args.window_seconds,
            max_images=args.max_images,
            max_segments_per_block=args.max_segments_per_block,
        )
        print(f"Wrote AI context: {ai_context_path}")
        print(f"Wrote Markdown review: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
