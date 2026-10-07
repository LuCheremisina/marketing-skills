#!/usr/bin/env python3
"""Export a project article cover to configurable PNG and WebP files."""

from __future__ import annotations

import argparse
import io
import re
from pathlib import Path

try:
    from PIL import Image, ImageCms, ImageOps
except ImportError:
    raise SystemExit("Pillow is required: install it in the approved project environment.")




def valid_slug(value: str) -> str:
    value = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise argparse.ArgumentTypeError(
            "slug must contain lowercase Latin letters, digits, and hyphens"
        )
    return value


def to_srgb(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    icc = image.info.get("icc_profile")
    if icc:
        try:
            source = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            target = ImageCms.createProfile("sRGB")
            return ImageCms.profileToProfile(image, source, target, outputMode="RGB")
        except (OSError, ValueError):
            raise ValueError("Input ICC profile cannot be converted to sRGB; supply a valid image")
    return image.convert("RGB")


def crop_16_9(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(
        image,
        size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def save_webp(image: Image.Image, path: Path, max_bytes: int) -> tuple[int, int]:
    for quality in range(88, 49, -3):
        buffer = io.BytesIO()
        image.save(buffer, "WEBP", quality=quality, method=6, icc_profile=None, exif=b"")
        data = buffer.getvalue()
        if len(data) <= max_bytes:
            with path.open("xb") as output:
                output.write(data)
            return quality, len(data)
    raise RuntimeError("Could not compress WebP under the requested limit without quality below 50")


def ensure_available(*paths: Path) -> None:
    collisions = [str(path) for path in paths if path.exists()]
    if collisions:
        raise SystemExit(
            "Refusing to overwrite existing file(s): " + ", ".join(collisions)
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--slug", required=True, type=valid_slug)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--png-width", type=int, default=1600)
    parser.add_argument("--png-height", type=int, default=900)
    parser.add_argument("--webp-width", type=int, default=1280)
    parser.add_argument("--webp-height", type=int, default=720)
    parser.add_argument("--max-kb", type=int, default=200)
    args = parser.parse_args()
    if min(args.png_width, args.png_height, args.webp_width, args.webp_height, args.max_kb) <= 0:
        parser.error("dimensions and max-kb must be positive")

    if not args.input.is_file():
        raise SystemExit(f"Input not found: {args.input}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    png_path = args.output_dir / f"{args.slug}-cover.png"
    webp_path = args.output_dir / f"{args.slug}-cover.webp"
    ensure_available(png_path, webp_path)

    with Image.open(args.input) as opened:
        source = to_srgb(opened)

    png = crop_16_9(source, (args.png_width, args.png_height))
    webp = crop_16_9(png, (args.webp_width, args.webp_height))
    quality, webp_bytes = save_webp(webp, webp_path, args.max_kb * 1024)
    png.save(png_path, "PNG", optimize=True, icc_profile=None, exif=b"")

    print(f"png={png_path} dimensions={png.width}x{png.height} colorspace=sRGB")
    print(
        f"webp={webp_path} dimensions={webp.width}x{webp.height} "
        f"bytes={webp_bytes} quality={quality} colorspace=sRGB"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(f"Export failed: {error}")
