import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from dotenv import load_dotenv


INTRADAY_COMMENTARY_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
DEFAULT_DAYS_BACK = 548  # Roughly 18 months.
DEFAULT_OUTPUT_DIR = Path("intraday_archives")
LOCAL_TZ = ZoneInfo("America/Toronto")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive intraday commentary Discord messages to a JSONL file."
    )
    parser.add_argument(
        "--channel-id",
        type=int,
        default=INTRADAY_COMMENTARY_CHANNEL_ID,
        help="Discord channel ID to archive.",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=DEFAULT_DAYS_BACK,
        help="How many days of history to pull. Default is about 18 months.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the archive file will be written.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help="Optional exact JSONL output path.",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=None,
        help="Optional safety limit for testing.",
    )
    parser.add_argument(
        "--no-download-images",
        action="store_true",
        help="Do not download image attachments locally.",
    )
    parser.add_argument(
        "--no-monthly-md",
        action="store_true",
        help="Do not create human-readable monthly Markdown files.",
    )
    return parser.parse_args()


def make_output_path(args: argparse.Namespace, cutoff_at: datetime) -> Path:
    if args.output_file:
        return args.output_file

    now = datetime.now(UTC)
    filename = (
        "intraday_commentary_"
        f"{cutoff_at:%Y-%m-%d}_to_{now:%Y-%m-%d_%H-%M-%S}.jsonl"
    )
    return args.output_dir / filename


def safe_name(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
    return cleaned.strip().replace(" ", "_") or "untitled"


def local_dt(dt: datetime) -> datetime:
    return dt.astimezone(LOCAL_TZ)


def attachment_kind(content_type: str | None) -> str:
    if not content_type:
        return "file"
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    if content_type.startswith("audio/"):
        return "audio"
    return "file"


def attachment_record(attachment: discord.Attachment) -> dict:
    return {
        "id": attachment.id,
        "filename": attachment.filename,
        "url": attachment.url,
        "proxy_url": attachment.proxy_url,
        "content_type": attachment.content_type,
        "kind": attachment_kind(attachment.content_type),
        "size": attachment.size,
        "width": attachment.width,
        "height": attachment.height,
        "description": attachment.description,
        "downloaded": False,
        "local_path": None,
        "download_error": None,
        "skipped_reason": None,
    }


def reference_record(message: discord.Message) -> dict | None:
    reference = message.reference

    if reference is None:
        return None

    return {
        "message_id": reference.message_id,
        "channel_id": reference.channel_id,
        "guild_id": reference.guild_id,
        "resolved_present": reference.resolved is not None,
        "resolved_type": type(reference.resolved).__name__ if reference.resolved else None,
    }


def snapshot_records(message: discord.Message) -> list[dict]:
    snapshots = getattr(message, "message_snapshots", None) or []
    records = []

    for snapshot in snapshots:
        records.append(
            {
                "content": getattr(snapshot, "content", None),
                "created_at": (
                    snapshot.created_at.isoformat()
                    if getattr(snapshot, "created_at", None)
                    else None
                ),
                "edited_at": (
                    snapshot.edited_at.isoformat()
                    if getattr(snapshot, "edited_at", None)
                    else None
                ),
                "attachments": [
                    attachment_record(attachment)
                    for attachment in getattr(snapshot, "attachments", [])
                ],
                "embeds": [
                    embed.to_dict()
                    for embed in getattr(snapshot, "embeds", [])
                ],
            }
        )

    return records


def message_to_record(message: discord.Message, attachments: list[dict]) -> dict:
    return {
        "message_id": message.id,
        "channel_id": message.channel.id,
        "channel_name": getattr(message.channel, "name", None),
        "guild_id": message.guild.id if message.guild else None,
        "guild_name": message.guild.name if message.guild else None,
        "author_id": message.author.id,
        "author_name": str(message.author),
        "created_at": message.created_at.isoformat(),
        "created_at_local": local_dt(message.created_at).isoformat(),
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "content": message.content,
        "clean_content": message.clean_content,
        "attachments": attachments,
        "embeds": [embed.to_dict() for embed in message.embeds],
        "reference": reference_record(message),
        "message_snapshots": snapshot_records(message),
        "jump_url": message.jump_url,
        "pinned": message.pinned,
        "tts": message.tts,
        "mention_everyone": message.mention_everyone,
    }


def print_progress(count: int, record: dict) -> None:
    preview = record["content"].replace("\n", " ").strip()
    if len(preview) > 120:
        preview = preview[:117] + "..."
    print(f"{count:>7} | {record['created_at']} | {record['author_name']} | {preview}")


async def prepare_attachments(
    message: discord.Message,
    attachment_dir: Path,
    download_images: bool,
) -> list[dict]:
    records = []
    local_time = local_dt(message.created_at)
    month_dir = attachment_dir / local_time.strftime("%Y-%m")
    filename_time = local_time.strftime("%Y-%m-%d_%H-%M")

    for index, attachment in enumerate(message.attachments, start=1):
        record = attachment_record(attachment)

        if record["kind"] != "image":
            record["skipped_reason"] = f"skipped_{record['kind']}"
            records.append(record)
            continue

        if not download_images:
            record["skipped_reason"] = "image_download_disabled"
            records.append(record)
            continue

        month_dir.mkdir(parents=True, exist_ok=True)
        filename = (
            f"{filename_time}_{message.id}_{index:02d}_"
            f"{safe_name(attachment.filename)}"
        )
        local_path = month_dir / filename

        try:
            await attachment.save(local_path)
        except Exception as exc:
            record["download_error"] = repr(exc)
        else:
            record["downloaded"] = True
            record["local_path"] = str(local_path)

        records.append(record)

    return records


def markdown_escape_heading(value: str | None) -> str:
    return (value or "unknown").replace("\n", " ").strip() or "unknown"


def markdown_for_message(record: dict, md_path: Path) -> str:
    created_at = datetime.fromisoformat(record["created_at_local"])
    header_time = created_at.strftime("%Y-%m-%d %H:%M")
    author = markdown_escape_heading(record["author_name"])
    content = record["clean_content"] or record["content"] or ""
    parts = [
        f"## {header_time} - {author}",
        "",
    ]

    if content.strip():
        parts.extend([content.strip(), ""])

    for attachment in record["attachments"]:
        local_path = attachment.get("local_path")
        filename = attachment.get("filename") or "attachment"
        kind = attachment.get("kind")

        if local_path:
            relative_path = os.path.relpath(local_path, start=md_path.parent)
            parts.extend([f"![{filename}]({Path(relative_path).as_posix()})", ""])
        elif attachment.get("url"):
            note = "skipped"
            if kind in {"video", "audio"}:
                note = f"skipped {kind}"
            elif attachment.get("download_error"):
                note = "download failed"
            parts.extend([f"[{filename}]({attachment['url']}) ({note})", ""])

    if record["embeds"]:
        for embed in record["embeds"]:
            url = embed.get("url")
            title = embed.get("title") or url
            if url:
                parts.extend([f"[{title}]({url})", ""])

    parts.extend([f"[Jump to Discord]({record['jump_url']})", "", "---", ""])
    return "\n".join(parts)


def write_monthly_markdown(record: dict, md_dir: Path) -> Path:
    created_at = datetime.fromisoformat(record["created_at_local"])
    month_path = md_dir / f"{created_at:%Y-%m}.md"
    month_path.parent.mkdir(parents=True, exist_ok=True)

    if not month_path.exists():
        month_path.write_text(
            f"# Intraday Commentary - {created_at:%B %Y}\n\n",
            encoding="utf-8",
        )

    with month_path.open("a", encoding="utf-8") as markdown_file:
        markdown_file.write(markdown_for_message(record, month_path))

    return month_path


async def archive_intraday_commentary(
    client: discord.Client,
    args: argparse.Namespace,
) -> None:
    if not args.channel_id:
        raise RuntimeError(
            "Missing Discord channel ID. Pass --channel-id or set DISCORD_CHANNEL_ID."
        )

    cutoff_at = datetime.now(UTC) - timedelta(days=args.days_back)
    output_path = make_output_path(args, cutoff_at)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    archive_stem = output_path.with_suffix("")
    attachment_dir = Path(f"{archive_stem}_attachments")
    md_dir = Path(f"{archive_stem}_months")
    download_images = not args.no_download_images
    create_monthly_md = not args.no_monthly_md

    channel = client.get_channel(args.channel_id)
    if channel is None:
        channel = await client.fetch_channel(args.channel_id)

    channel_name = getattr(channel, "name", None)
    print(f"Archiving #{channel_name or args.channel_id}")
    print(f"Cutoff: {cutoff_at.isoformat()}")
    print(f"Output: {output_path}")
    if download_images:
        print(f"Image attachments: {attachment_dir}")
    else:
        print("Image attachments: disabled")
    if create_monthly_md:
        print(f"Monthly Markdown: {md_dir}")
    else:
        print("Monthly Markdown: disabled")
    print()

    count = 0
    downloaded_images = 0
    skipped_attachments = 0
    failed_downloads = 0
    markdown_months = set()

    with output_path.open("w", encoding="utf-8") as output_file:
        async for message in channel.history(
            limit=args.max_messages,
            after=cutoff_at,
            oldest_first=True,
        ):
            attachments = await prepare_attachments(
                message,
                attachment_dir,
                download_images,
            )
            record = message_to_record(message, attachments)
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
            downloaded_images += sum(1 for item in attachments if item["downloaded"])
            skipped_attachments += sum(1 for item in attachments if item["skipped_reason"])
            failed_downloads += sum(1 for item in attachments if item["download_error"])

            if create_monthly_md:
                markdown_months.add(write_monthly_markdown(record, md_dir))

            if count == 1 or count % 25 == 0:
                print_progress(count, record)

    manifest_path = output_path.with_suffix(".manifest.json")
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "channel_id": args.channel_id,
        "channel_name": channel_name,
        "cutoff_at": cutoff_at.isoformat(),
        "days_back": args.days_back,
        "message_count": count,
        "jsonl_file": str(output_path),
        "downloaded_images": downloaded_images,
        "skipped_attachments": skipped_attachments,
        "failed_downloads": failed_downloads,
        "attachment_dir": str(attachment_dir) if download_images else None,
        "monthly_markdown_dir": str(md_dir) if create_monthly_md else None,
        "monthly_markdown_files": [str(path) for path in sorted(markdown_months)],
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nDone. Saved {count} messages to {output_path}")
    print(f"Downloaded {downloaded_images} image attachments")
    print(f"Skipped {skipped_attachments} non-image or disabled attachments")
    if failed_downloads:
        print(f"Failed to download {failed_downloads} attachments")
    if create_monthly_md:
        print(f"Saved {len(markdown_months)} monthly Markdown files to {md_dir}")
    print(f"Saved run summary to {manifest_path}")


def main() -> None:
    args = parse_args()
    load_dotenv()

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN in your environment or .env file.")

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        print(f"Logged in as {client.user}")
        try:
            await archive_intraday_commentary(client, args)
        finally:
            await client.close()

    client.run(token)


if __name__ == "__main__":
    main()
