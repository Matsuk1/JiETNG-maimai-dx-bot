#!/usr/bin/env python3
"""Atomically replace legacy cover-cache images with WebP files."""

import argparse
import os
from pathlib import Path

from PIL import Image


SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}


def convert_directory(directory: Path, quality: int = 90):
    converted = 0
    removed_bytes = 0
    written_bytes = 0
    failures = []

    for source in sorted(directory.iterdir()):
        if not source.is_file() or source.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        target = source.with_suffix(".webp")
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        try:
            source_bytes = source.stat().st_size
            with Image.open(source) as opened:
                image = opened.convert("RGBA" if "A" in opened.getbands() else "RGB")
                expected_size = opened.size
            try:
                image.save(temporary, format="WEBP", quality=quality, method=4)
            finally:
                image.close()
            with Image.open(temporary) as check:
                check.verify()
            with Image.open(temporary) as check:
                if check.size != expected_size or check.format != "WEBP":
                    raise ValueError(f"invalid converted image: {check.format} {check.size}")
            os.replace(temporary, target)
            target_bytes = target.stat().st_size
            source.unlink()
            converted += 1
            removed_bytes += source_bytes
            written_bytes += target_bytes
        except Exception as exc:
            failures.append((source.name, str(exc)))
            temporary.unlink(missing_ok=True)

    return converted, removed_bytes, written_bytes, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", default="assets/covers", type=Path)
    parser.add_argument("--quality", type=int, default=90)
    args = parser.parse_args()
    if not args.directory.is_dir():
        raise SystemExit(f"cover directory not found: {args.directory}")

    converted, before, after, failures = convert_directory(args.directory, args.quality)
    print(
        f"converted={converted} before_mb={before / 1048576:.1f} "
        f"after_mb={after / 1048576:.1f} saved_mb={(before - after) / 1048576:.1f} "
        f"failures={len(failures)}"
    )
    for name, error in failures:
        print(f"FAILED {name}: {error}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
