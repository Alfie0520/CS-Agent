"""从公众号永久素材 media_id 恢复本地图片资产。"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.assets.image_processing import compress_image_if_needed
from app.assets.index import rescan_image_assets

DownloadMaterial = Callable[[str], Awaitable[dict[str, Any]]]


def restore_assets_from_media_index(
    media_index_path: str | Path,
    asset_root: str | Path,
    asset_index_path: str | Path,
    download_material: DownloadMaterial,
    threshold_bytes: int = 1024 * 1024,
    target_bytes: int = 200 * 1024,
) -> dict[str, Any]:
    """按旧 media_index 下载永久素材图片，恢复到本地资产目录。"""
    return asyncio.run(
        _restore_assets_from_media_index_async(
            media_index_path=Path(media_index_path),
            asset_root=Path(asset_root),
            asset_index_path=Path(asset_index_path),
            download_material=download_material,
            threshold_bytes=threshold_bytes,
            target_bytes=target_bytes,
        )
    )


async def _restore_assets_from_media_index_async(
    media_index_path: Path,
    asset_root: Path,
    asset_index_path: Path,
    download_material: DownloadMaterial,
    threshold_bytes: int,
    target_bytes: int,
) -> dict[str, Any]:
    items = json.loads(media_index_path.read_text(encoding="utf-8"))
    restored = 0
    already_exists = 0
    skipped: list[dict[str, str]] = []

    for item in items if isinstance(items, list) else []:
        media_id = (item.get("media_id") or "").strip()
        image_name = (item.get("image_name") or "").strip()
        category = (item.get("category") or "").strip()
        if not media_id or not image_name:
            skipped.append({"media_id": media_id, "reason": "missing media_id or image_name"})
            continue

        try:
            target_path = _target_image_path(asset_root, category, image_name)
        except ValueError as e:
            skipped.append({"media_id": media_id, "reason": str(e)})
            continue

        if target_path.exists() or target_path.with_suffix(".jpg").exists():
            already_exists += 1
            continue

        try:
            result = await download_material(media_id)
            content = result.get("content")
            if not isinstance(content, (bytes, bytearray)):
                skipped.append({"media_id": media_id, "reason": str(result.get("errmsg") or result)})
                continue

            with tempfile.TemporaryDirectory() as tmpdir:
                suffix = target_path.suffix or _suffix_from_content_type(result.get("content_type", ""))
                raw_path = Path(tmpdir) / f"raw{suffix}"
                raw_path.write_bytes(bytes(content))
                final_path = target_path
                if raw_path.stat().st_size > threshold_bytes:
                    final_path = target_path.with_suffix(".jpg")
                _atomic_replace_image(
                    raw_path=raw_path,
                    target_path=final_path,
                    threshold_bytes=threshold_bytes,
                    target_bytes=target_bytes,
                )
        except Exception as e:
            skipped.append({"media_id": media_id, "reason": str(e)})
            continue
        restored += 1

    assets = rescan_image_assets(asset_root, asset_index_path)
    return {
        "restored": restored,
        "already_exists": already_exists,
        "skipped": skipped,
        "asset_count": len(assets),
    }


def _target_image_path(asset_root: Path, category: str, image_name: str) -> Path:
    category_path = Path(category)
    if category_path.is_absolute() or ".." in category_path.parts:
        raise ValueError("invalid category")
    if Path(image_name).name != image_name:
        raise ValueError("invalid image_name")
    return asset_root / "images" / category_path / image_name


def _atomic_replace_image(
    raw_path: Path,
    target_path: Path,
    threshold_bytes: int,
    target_bytes: int,
) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_target = target_path.with_name(f".{target_path.name}.tmp")
    compress_image_if_needed(raw_path, tmp_target, threshold_bytes, target_bytes)
    os.replace(tmp_target, target_path)


def _suffix_from_content_type(content_type: str) -> str:
    content_type = content_type.lower().split(";")[0].strip()
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/webp": ".webp",
    }.get(content_type, ".jpg")
