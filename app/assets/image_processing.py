"""图片压缩工具。"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageFile, ImageOps

ImageFile.LOAD_TRUNCATED_IMAGES = True


def compress_image_if_needed(
    source_path: str | Path,
    target_path: str | Path,
    threshold_bytes: int = 1024 * 1024,
    target_bytes: int = 200 * 1024,
) -> Path:
    """当源图片超过阈值时，压缩为 JPEG 并尽量接近目标大小。"""
    source = Path(source_path)
    target = Path(target_path)
    if source.stat().st_size <= threshold_bytes:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target.resolve():
            target.write_bytes(source.read_bytes())
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        ):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
            img = background
        else:
            img = img.convert("RGB")

        work = _resize_to_max_side(img, 1600)
        while True:
            best_bytes: bytes | None = None
            for quality in (78, 68, 58, 48, 38, 30):
                encoded = _encode_jpeg(work, quality)
                best_bytes = encoded
                if len(encoded) <= target_bytes:
                    target.write_bytes(encoded)
                    return target

            if best_bytes and len(best_bytes) <= int(target_bytes * 1.3):
                target.write_bytes(best_bytes)
                return target

            width, height = work.size
            if width <= 640 or height <= 640:
                target.write_bytes(best_bytes or _encode_jpeg(work, 22))
                return target

            next_size = (max(640, int(width * 0.82)), max(640, int(height * 0.82)))
            work = work.resize(next_size, Image.Resampling.LANCZOS)


def _encode_jpeg(image: Image.Image, quality: int) -> bytes:
    from io import BytesIO

    buf = BytesIO()
    image.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def _resize_to_max_side(image: Image.Image, max_side: int) -> Image.Image:
    width, height = image.size
    current_max = max(width, height)
    if current_max <= max_side:
        return image
    scale = max_side / current_max
    next_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(next_size, Image.Resampling.LANCZOS)
