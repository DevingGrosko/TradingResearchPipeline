# Video Pipeline

Caption-first tooling for converting trading videos into research-friendly transcript and image artifacts.

## What This Folder Does

- Parses existing `.vtt`, `.srt`, or timestamped `.txt` captions.
- Extracts chart frames from video files with PyAV and Pillow.
- Builds JSON transcript files with segment metadata.
- Links transcript segments to nearby screenshots for AI/context review.
- Generates Markdown review files for human inspection.

## Data Policy

Video files, screenshots, transcript outputs, and generated JSON archives are excluded from the public repo.

