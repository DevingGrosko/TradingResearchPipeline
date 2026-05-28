from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import transcribe


DEFAULT_ARCHIVE_ROOT = transcribe.DEFAULT_ARCHIVE_DAYS_ROOT


def clean_name(raw: str) -> str:
    name = Path(raw).stem if Path(raw).suffix else raw
    return "".join("-" if char in '/\\:' else char for char in name).strip()


def run_command(command: list[str], dry_run: bool) -> None:
    print("$ " + " ".join(command))
    if dry_run:
        return
    subprocess.run(command, check=True)


def download_captions(
    url: str,
    title: str,
    captions_dir: Path,
    force: bool,
    dry_run: bool,
) -> Path:
    captions_dir.mkdir(parents=True, exist_ok=True)
    caption_path = captions_dir / f"{title}.en.vtt"
    if caption_path.exists() and not force:
        print(f"Using existing captions: {caption_path}")
        return caption_path

    output_template = captions_dir / f"{title}.%(ext)s"
    command = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "en",
        "--sub-format",
        "vtt",
        "-o",
        str(output_template),
        url,
    ]
    run_command(command, dry_run)
    return caption_path


def download_video(
    url: str,
    title: str,
    input_dir: Path,
    video_format: str,
    force: bool,
    dry_run: bool,
) -> Path:
    input_dir.mkdir(parents=True, exist_ok=True)
    video_path = input_dir / f"{title}.mp4"
    if video_path.exists() and not force:
        print(f"Using existing video: {video_path}")
        return video_path

    output_template = input_dir / f"{title}.%(ext)s"
    command = [
        "yt-dlp",
        "-f",
        video_format,
        "--merge-output-format",
        "mp4",
        "-o",
        str(output_template),
        url,
    ]
    run_command(command, dry_run)
    return video_path


def process_archive(
    video_path: Path,
    archive_root: Path,
    day_folder: str,
    captions_dir: Path,
    dry_run: bool,
) -> Path:
    command = [
        sys.executable,
        str(Path(__file__).resolve().parent / "transcribe.py"),
        str(video_path),
        "--archive-root",
        str(archive_root),
        "--day-folder",
        day_folder,
        "--captions-dir",
        str(captions_dir),
        "--language",
        "en",
        "--image-width",
        "0",
        "--image-crops",
        "none",
        "--jpeg-quality",
        "95",
    ]
    run_command(command, dry_run)
    return archive_root / day_folder / "json" / f"{transcribe.safe_stem(video_path)}.json"


def build_context(source_json: Path, dry_run: bool) -> None:
    command = [
        sys.executable,
        str(Path(__file__).resolve().parent / "build_context.py"),
        str(source_json),
        "--window-seconds",
        "20",
        "--max-images",
        "3",
        "--max-segments-per-block",
        "12",
    ]
    run_command(command, dry_run)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a Mux video, pull captions, generate screenshots/transcript, and build AI context."
    )
    parser.add_argument("url", help="Mux .m3u8 URL.")
    parser.add_argument(
        "--name",
        required=True,
        help="Video/archive file name, for example 'May 8th Daily Review'.",
    )
    parser.add_argument(
        "--day-folder",
        "--folder-name",
        dest="day_folder",
        default=None,
        help="Archive day folder, for example 2026-05-08. If omitted, inferred from --name.",
    )
    parser.add_argument(
        "--archive-root",
        default=str(DEFAULT_ARCHIVE_ROOT),
        help=f"Destination archive root. Default: {DEFAULT_ARCHIVE_ROOT}",
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Where downloaded MP4s are stored. Default: <AudioTranscripts: For videos>/input_videos",
    )
    parser.add_argument(
        "--captions-dir",
        default=None,
        help="Where downloaded captions are stored. Default: <AudioTranscripts: For videos>/captions",
    )
    parser.add_argument(
        "--video-format",
        default="bv*+ba/b",
        help="yt-dlp format selector. Default downloads the best video+audio available.",
    )
    parser.add_argument("--force", action="store_true", help="Redownload/rewrite existing video or captions.")
    parser.add_argument("--skip-context", action="store_true", help="Do not build AI-context JSON/Markdown.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands and paths without running them.")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    title = clean_name(args.name)
    if not title:
        raise SystemExit("--name cannot be empty.")

    day_folder = args.day_folder or transcribe.infer_day_folder(Path(title), 2026)
    if not day_folder:
        raise SystemExit("Could not infer day folder from --name. Pass --day-folder YYYY-MM-DD.")

    archive_root = Path(args.archive_root).expanduser()
    input_dir = Path(args.input_dir).expanduser() if args.input_dir else project_root / "input_videos"
    captions_dir = Path(args.captions_dir).expanduser() if args.captions_dir else project_root / "captions"

    print(f"Name: {title}")
    print(f"Day folder: {day_folder}")
    print(f"Archive root: {archive_root}")
    print(f"Input videos: {input_dir}")
    print(f"Captions: {captions_dir}")

    download_captions(
        url=args.url,
        title=title,
        captions_dir=captions_dir,
        force=args.force,
        dry_run=args.dry_run,
    )
    video_path = download_video(
        url=args.url,
        title=title,
        input_dir=input_dir,
        video_format=args.video_format,
        force=args.force,
        dry_run=args.dry_run,
    )
    source_json = process_archive(
        video_path=video_path,
        archive_root=archive_root,
        day_folder=day_folder,
        captions_dir=captions_dir,
        dry_run=args.dry_run,
    )
    if not args.skip_context:
        build_context(source_json, args.dry_run)

    print(f"Done: {archive_root / day_folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
