from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS
DEFAULT_ARCHIVE_DAYS_ROOT = (
    Path(__file__).resolve().parents[2] / "FearingArchive: All fearing stuff" / "Days"
)
MONTHS = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}


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


def safe_stem(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem).strip("_") or "transcript"


def infer_day_folder(path: Path, year: int) -> str | None:
    match = re.search(
        r"\b("
        + "|".join(re.escape(month) for month in sorted(MONTHS, key=len, reverse=True))
        + r")\s*(\d{1,2})(?:st|nd|rd|th)?(?=\b|[A-Z_])",
        path.stem,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    month = MONTHS[match.group(1).lower()]
    day = int(match.group(2))
    return f"{year}-{month}-{day:02d}"


def filename_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds_part = total_seconds % 60
    if hours:
        return f"{hours:02d}h{minutes:02d}m{seconds_part:02d}s"
    return f"{minutes:02d}m{seconds_part:02d}s"


def iter_media(inputs: list[str], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for raw in inputs:
        path = Path(raw).expanduser()
        if path.is_dir():
            globber = path.rglob if recursive else path.glob
            files.extend(p for p in globber("*") if p.suffix.lower() in MEDIA_EXTENSIONS)
        elif path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS:
            files.append(path)
        else:
            print(f"Skipping unsupported input: {path}", file=sys.stderr)
    return sorted(dict.fromkeys(files))


def parse_vtt_timestamp(value: str) -> float:
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours = "0"
        minutes, seconds = parts
    else:
        raise ValueError(f"Unsupported VTT timestamp: {value}")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def clean_caption_text(line: str) -> str:
    line = re.sub(r"<[^>]+>", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def parse_vtt_file(caption_path: Path) -> list[dict[str, Any]]:
    blocks = re.split(r"\n\s*\n", caption_path.read_text(encoding="utf-8-sig"))
    segments: list[dict[str, Any]] = []
    previous_text = ""

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or lines[0].startswith("WEBVTT") or lines[0].startswith("Kind:"):
            continue

        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue

        start_raw, end_raw = lines[timing_index].split("-->", 1)
        end_raw = end_raw.split()[0]
        text = " ".join(clean_caption_text(line) for line in lines[timing_index + 1 :])
        text = re.sub(r"\s+", " ", text).strip()
        if not text or text == previous_text:
            continue

        segments.append(
            {
                "start": round(parse_vtt_timestamp(start_raw), 3),
                "end": round(parse_vtt_timestamp(end_raw), 3),
                "text": text,
            }
        )
        previous_text = text

    return segments


def parse_srt_file(caption_path: Path) -> list[dict[str, Any]]:
    blocks = re.split(r"\n\s*\n", caption_path.read_text(encoding="utf-8-sig"))
    segments: list[dict[str, Any]] = []
    previous_text = ""

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue

        start_raw, end_raw = lines[timing_index].split("-->", 1)
        end_raw = end_raw.split()[0]
        text = " ".join(clean_caption_text(line) for line in lines[timing_index + 1 :])
        text = re.sub(r"\s+", " ", text).strip()
        if not text or text == previous_text:
            continue

        segments.append(
            {
                "start": round(parse_vtt_timestamp(start_raw), 3),
                "end": round(parse_vtt_timestamp(end_raw), 3),
                "text": text,
            }
        )
        previous_text = text

    return segments


def parse_timestamped_text_file(caption_path: Path) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    pattern = re.compile(r"^\[(?P<start>[^\]-]+)-(?P<end>[^\]]+)\]\s*(?P<text>.*)$")
    for line in caption_path.read_text(encoding="utf-8-sig").splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        text = re.sub(r"\s+", " ", match.group("text")).strip()
        if not text:
            continue
        segments.append(
            {
                "start": round(parse_vtt_timestamp(match.group("start")), 3),
                "end": round(parse_vtt_timestamp(match.group("end")), 3),
                "text": text,
            }
        )
    return segments


def parse_caption_file(caption_path: Path) -> list[dict[str, Any]]:
    suffix = caption_path.suffix.lower()
    if suffix == ".vtt":
        return parse_vtt_file(caption_path)
    if suffix == ".srt":
        return parse_srt_file(caption_path)
    if suffix == ".txt":
        return parse_timestamped_text_file(caption_path)
    raise SystemExit(f"Unsupported caption/transcript file type: {caption_path}")


def find_caption_file(media_path: Path, captions_dir: Path | None) -> Path | None:
    if captions_dir is None:
        return None

    candidates = [
        captions_dir / f"{media_path.stem}.en.vtt",
        captions_dir / f"{media_path.stem}.vtt",
        captions_dir / f"{media_path.stem}.en.srt",
        captions_dir / f"{media_path.stem}.srt",
        captions_dir / f"{media_path.stem}.txt",
        media_path.with_suffix(".en.vtt"),
        media_path.with_suffix(".vtt"),
        media_path.with_suffix(".en.srt"),
        media_path.with_suffix(".srt"),
        media_path.with_suffix(".txt"),
    ]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def parse_image_crops(raw: str) -> list[str]:
    if not raw or raw.lower() in {"none", "off", "false"}:
        return []
    aliases = {
        "axis": ["right-axis", "bottom-axis"],
        "axes": ["right-axis", "bottom-axis"],
        "default": [],
    }
    crops: list[str] = []
    for item in re.split(r"[, ]+", raw.strip().lower()):
        if not item:
            continue
        for crop in aliases.get(item, [item]):
            if crop not in {"right-axis", "bottom-axis", "bottom-right"}:
                raise SystemExit(f"Unsupported image crop: {crop}")
            if crop not in crops:
                crops.append(crop)
    return crops


def write_media_outputs(
    media_path: Path,
    output_dir: Path,
    source_kind: str,
    source_name: str,
    language: str | None,
    duration: float | None,
    segment_rows: list[dict[str, Any]],
    capture_images: bool,
    frame_interval: float,
    scene_check_interval: float,
    scene_threshold: float,
    scene_min_gap: float,
    max_frames: int,
    image_width: int,
    image_crops: list[str],
    jpeg_quality: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_dir = output_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)

    stem = safe_stem(media_path)
    text_lines = [
        f"[{timestamp(row['start'])}-{timestamp(row['end'])}] {row['text']}"
        for row in segment_rows
    ]

    transcript_path = output_dir / f"{stem}.txt"
    json_path = json_dir / f"{stem}.json"
    image_manifest = None

    if capture_images:
        print(f"Capturing video images: {media_path}")
        image_manifest = capture_video_images(
            media_path=media_path,
            output_dir=output_dir,
            interval_seconds=frame_interval,
            check_interval=scene_check_interval,
            scene_threshold=scene_threshold,
            scene_min_gap=scene_min_gap,
            max_frames=max_frames,
            image_width=image_width,
            image_crops=image_crops,
            jpeg_quality=jpeg_quality,
        )

    transcript_path.write_text("\n".join(text_lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "source": str(media_path),
                "source_kind": source_kind,
                "source_name": source_name,
                "language": language,
                "duration": duration,
                "segments": segment_rows,
                "images": image_manifest,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote transcript: {transcript_path}")
    print(f"Wrote segment JSON: {json_path}")
    if image_manifest:
        print(f"Wrote {image_manifest['count']} images: {image_manifest['directory']}")


def video_duration(container: Any, stream: Any) -> float | None:
    if container.duration:
        return float(container.duration / 1_000_000)
    if stream.duration and stream.time_base:
        return float(stream.duration * stream.time_base)
    return None


def sample_video_frames(media_path: Path, check_interval: float) -> Iterable[tuple[float, Any]]:
    try:
        import av
    except ImportError as exc:
        raise SystemExit(
            "Missing PyAV. Install with: pip install -r requirements.txt"
        ) from exc

    with av.open(str(media_path)) as container:
        video_streams = [stream for stream in container.streams if stream.type == "video"]
        if not video_streams:
            return

        stream = video_streams[0]
        stream.thread_type = "AUTO"
        duration = video_duration(container, stream)

        target_time = 0.0
        last_seen_time = -1.0
        while duration is None or target_time <= duration:
            try:
                if stream.time_base:
                    seek_offset = int(target_time / float(stream.time_base))
                    container.seek(seek_offset, stream=stream, backward=True)
                else:
                    container.seek(int(target_time * 1_000_000), backward=True)
            except Exception:
                break

            selected_frame = None
            selected_time = None
            for frame in container.decode(stream):
                frame_time = frame.time
                if frame_time is None and frame.pts is not None and stream.time_base:
                    frame_time = float(frame.pts * stream.time_base)
                if frame_time is None:
                    continue
                selected_frame = frame
                selected_time = float(frame_time)
                if selected_time >= target_time - 0.25:
                    break

            if selected_frame is None or selected_time is None:
                break
            if selected_time > last_seen_time + 0.5:
                yield selected_time, selected_frame
                last_seen_time = selected_time

            target_time += check_interval
            if duration is None and target_time > last_seen_time + check_interval * 3:
                break


def image_signature(image: Any) -> Any:
    from PIL import Image

    signature = image.convert("L")
    signature.thumbnail((96, 54), Image.Resampling.LANCZOS)
    return signature


def scene_change_score(previous: Any | None, current: Any) -> float | None:
    if previous is None:
        return None

    from PIL import ImageChops, ImageStat

    diff = ImageChops.difference(previous, current)
    return float(ImageStat.Stat(diff).mean[0])


def require_pillow() -> None:
    try:
        import PIL  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Missing Pillow. Install with: pip install -r requirements.txt"
        ) from exc


def resize_image(image: Any, max_width: int) -> Any:
    from PIL import Image

    if max_width and image.width > max_width:
        height = round(image.height * (max_width / image.width))
        return image.resize((max_width, height), Image.Resampling.LANCZOS)
    return image


def crop_box(image: Any, crop_name: str) -> tuple[int, int, int, int]:
    width, height = image.size
    if crop_name == "right-axis":
        return (round(width * 0.78), 0, width, height)
    if crop_name == "bottom-axis":
        return (0, round(height * 0.78), width, height)
    if crop_name == "bottom-right":
        return (round(width * 0.68), round(height * 0.62), width, height)
    raise SystemExit(f"Unsupported image crop: {crop_name}")


def save_jpeg(image: Any, output_path: Path, jpeg_quality: int) -> None:
    image.save(output_path, "JPEG", quality=jpeg_quality, optimize=True)


def save_frame_assets(
    frame: Any,
    image_root: Path,
    image_name: str,
    crop_names: list[str],
    max_width: int,
    jpeg_quality: int,
) -> tuple[Path, dict[str, Any]]:
    image = frame.to_image()
    if image.mode != "RGB":
        image = image.convert("RGB")

    full_image = resize_image(image, max_width)
    image_path = image_root / image_name
    save_jpeg(full_image, image_path, jpeg_quality)

    derivatives: list[dict[str, Any]] = []
    for crop_name in crop_names:
        box = crop_box(image, crop_name)
        crop = image.crop(box)
        crop_file = f"{Path(image_name).stem}__{crop_name.replace('-', '_')}.jpg"
        crop_path = image_root / crop_file
        save_jpeg(crop, crop_path, jpeg_quality)
        derivatives.append(
            {
                "role": crop_name,
                "file": crop_file,
                "path": str(crop_path),
                "box": list(box),
                "width": crop.width,
                "height": crop.height,
            }
        )

    return image_path, {
        "width": full_image.width,
        "height": full_image.height,
        "source_width": image.width,
        "source_height": image.height,
        "derivatives": derivatives,
    }


def capture_video_images(
    media_path: Path,
    output_dir: Path,
    interval_seconds: float,
    check_interval: float,
    scene_threshold: float,
    scene_min_gap: float,
    max_frames: int,
    image_width: int,
    image_crops: list[str],
    jpeg_quality: int,
) -> dict[str, Any] | None:
    if media_path.suffix.lower() not in VIDEO_EXTENSIONS:
        return None

    if interval_seconds <= 0 and scene_threshold <= 0:
        return None
    if check_interval <= 0:
        raise SystemExit("--scene-check-interval must be greater than 0.")

    require_pillow()

    image_root = output_dir / "images" / safe_stem(media_path)
    image_root.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "source": str(media_path),
        "interval_seconds": interval_seconds,
        "scene_check_interval": check_interval,
        "scene_threshold": scene_threshold,
        "image_width": image_width,
        "image_crops": image_crops,
        "frames": [],
    }

    previous_signature = None
    last_saved_time = -1_000_000.0
    last_interval_time = -1_000_000.0

    for sample_time, frame in sample_video_frames(media_path, check_interval):
        pil_image = frame.to_image()
        signature = image_signature(pil_image)
        score = scene_change_score(previous_signature, signature)
        previous_signature = signature

        reasons: list[str] = []
        if not manifest["frames"]:
            reasons.append("first-frame")
        if interval_seconds > 0 and sample_time - last_interval_time >= interval_seconds:
            reasons.append("interval")
        if (
            score is not None
            and scene_threshold > 0
            and score >= scene_threshold
            and sample_time - last_saved_time >= scene_min_gap
        ):
            reasons.append("scene-change")

        if not reasons:
            continue

        frame_number = len(manifest["frames"]) + 1
        image_name = f"{safe_stem(media_path)}_{frame_number:04d}_{filename_timestamp(sample_time)}.jpg"
        image_path, image_meta = save_frame_assets(
            frame=frame,
            image_root=image_root,
            image_name=image_name,
            crop_names=image_crops,
            max_width=image_width,
            jpeg_quality=jpeg_quality,
        )

        if "interval" in reasons:
            last_interval_time = sample_time
        last_saved_time = sample_time

        manifest["frames"].append(
            {
                "file": image_name,
                "path": str(image_path),
                "time": round(sample_time, 3),
                "timestamp": timestamp(sample_time),
                "reason": reasons,
                "scene_score": None if score is None else round(score, 3),
                **image_meta,
            }
        )

        if max_frames > 0 and len(manifest["frames"]) >= max_frames:
            manifest["truncated"] = True
            break

    manifest_path = image_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {
        "directory": str(image_root),
        "manifest": str(manifest_path),
        "count": len(manifest["frames"]),
    }


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert existing closed captions/transcripts into text/JSON and extract video images."
    )
    parser.add_argument("inputs", nargs="+", help="Media files or folders.")
    parser.add_argument("--recursive", action="store_true", help="Recurse into folders.")
    parser.add_argument("--output-dir", default="transcripts", help="Output directory.")
    parser.add_argument(
        "--archive-root",
        nargs="?",
        const=str(DEFAULT_ARCHIVE_DAYS_ROOT),
        default=None,
        help=f"Write into a day folder under this archive root. Default root: {DEFAULT_ARCHIVE_DAYS_ROOT}",
    )
    parser.add_argument(
        "--day-folder",
        default=None,
        help="Day folder name to use with --archive-root. Defaults to today's YYYY-MM-DD.",
    )
    parser.add_argument(
        "--auto-day-folder",
        action="store_true",
        help="Infer YYYY-MM-DD day folders from media filenames like 'Jan 20 Daily Review'.",
    )
    parser.add_argument(
        "--archive-year",
        type=int,
        default=2026,
        help="Year to use with --auto-day-folder.",
    )
    parser.add_argument(
        "--captions-dir",
        default="captions",
        help="Folder containing matching Whop closed captions/transcripts. Relative paths resolve from this project.",
    )
    parser.add_argument("--language", default="en", help="Language code or empty for auto.")
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Disable video frame capture.",
    )
    parser.add_argument(
        "--frame-interval",
        type=float,
        default=30.0,
        help="Save a video image at least this often, in seconds. Use 0 to disable interval captures.",
    )
    parser.add_argument(
        "--scene-check-interval",
        type=float,
        default=5.0,
        help="How often to sample the video while looking for scene changes.",
    )
    parser.add_argument(
        "--scene-threshold",
        type=float,
        default=18.0,
        help="Average pixel difference needed to save an extra scene-change image. Use 0 to disable.",
    )
    parser.add_argument(
        "--scene-min-gap",
        type=float,
        default=8.0,
        help="Minimum seconds between scene-change image captures.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=200,
        help="Maximum images to save per video. Use 0 for no limit.",
    )
    parser.add_argument(
        "--image-width",
        type=int,
        default=0,
        help="Resize captured images to this maximum width. Use 0 for original size.",
    )
    parser.add_argument(
        "--image-crops",
        default="none",
        help="Comma-separated crops to save with each frame. Use none to disable crops.",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=95,
        help="JPEG quality for captured images.",
    )
    return parser.parse_args(list(argv))


def resolve_output_dir(args: argparse.Namespace, base_dir: Path) -> Path:
    if args.archive_root is not None:
        archive_root = Path(args.archive_root or DEFAULT_ARCHIVE_DAYS_ROOT).expanduser()
        day_folder = args.day_folder or date.today().isoformat()
        return archive_root / day_folder

    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = base_dir / output_dir
    return output_dir


def resolve_output_dir_for_media(args: argparse.Namespace, base_dir: Path, media_path: Path) -> Path:
    if args.archive_root is not None and args.auto_day_folder:
        archive_root = Path(args.archive_root or DEFAULT_ARCHIVE_DAYS_ROOT).expanduser()
        day_folder = infer_day_folder(media_path, args.archive_year) or args.day_folder or date.today().isoformat()
        return archive_root / day_folder
    return resolve_output_dir(args, base_dir)


def resolve_captions_dir(raw: str | None, base_dir: Path) -> Path | None:
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    base_dir = Path(__file__).resolve().parents[1]
    image_crops = parse_image_crops(args.image_crops)

    captions_dir = resolve_captions_dir(args.captions_dir, base_dir)

    media_files = iter_media(args.inputs, args.recursive)
    if not media_files:
        print("No media files found.", file=sys.stderr)
        return 1

    caption_paths = {
        media_path: find_caption_file(media_path, captions_dir) for media_path in media_files
    }
    missing_captions = [
        media_path for media_path, caption_path in caption_paths.items() if caption_path is None
    ]
    if missing_captions:
        missing = "\n".join(f"- {path}" for path in missing_captions)
        captions_location = captions_dir if captions_dir is not None else "next to the video file"
        raise SystemExit(
            "Missing Whop closed captions/transcript file for:\n"
            f"{missing}\n\n"
            "Audio transcription is disabled for this project. Put a matching "
            f".vtt, .srt, or timestamped .txt file in {captions_location} "
            "or next to the video, using the same base filename."
        )

    language = args.language or None
    for media_path in media_files:
        output_dir = resolve_output_dir_for_media(args, base_dir, media_path)
        caption_path = caption_paths[media_path]
        assert caption_path is not None
        print(f"Using captions: {caption_path}")
        segment_rows = parse_caption_file(caption_path)
        if not segment_rows:
            raise SystemExit(f"No timestamped caption segments found in {caption_path}")
        write_media_outputs(
            media_path=media_path,
            output_dir=output_dir,
            source_kind="captions",
            source_name=str(caption_path),
            language=language or "en",
            duration=segment_rows[-1]["end"],
            segment_rows=segment_rows,
            capture_images=not args.no_images,
            frame_interval=args.frame_interval,
            scene_check_interval=args.scene_check_interval,
            scene_threshold=args.scene_threshold,
            scene_min_gap=args.scene_min_gap,
            max_frames=args.max_frames,
            image_width=args.image_width,
            image_crops=image_crops,
            jpeg_quality=args.jpeg_quality,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
