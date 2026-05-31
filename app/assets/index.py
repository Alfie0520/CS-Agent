"""本地业务图片资产索引。

资产文件存放在 asset_root/images 下，索引是由文件结构扫描得到的缓存。
Agent 只接触 asset_id，不直接接触服务器文件路径。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_asset_part(value: str) -> str:
    value = value.strip().replace("\\", "/")
    value = re.sub(r"\s+", " ", value)
    return value


def build_image_asset_index(images_root: str | Path) -> list[dict[str, Any]]:
    """扫描图片目录，生成稳定的图片资产索引。"""
    root = Path(images_root)
    if not root.exists():
        return []

    assets: list[dict[str, Any]] = []
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in _IMAGE_SUFFIXES:
            continue

        rel_to_images = file_path.relative_to(root)
        category_path = rel_to_images.parent
        category = "" if str(category_path) == "." else category_path.as_posix()
        name = file_path.stem
        asset_id = f"visit_image:{_safe_asset_part(category)}:{_safe_asset_part(name)}"
        rel_to_asset_root = Path("images") / rel_to_images

        assets.append(
            {
                "asset_id": asset_id,
                "kind": "image",
                "name": name,
                "category": category,
                "path": rel_to_asset_root.as_posix(),
                "sha256": _sha256(file_path),
                "size": file_path.stat().st_size,
                "enterprise_names": [name],
            }
        )

    return assets


def save_asset_index(assets: list[dict[str, Any]], index_path: str | Path) -> None:
    _atomic_write_json(Path(index_path), assets)


def load_asset_index(index_path: str | Path) -> list[dict[str, Any]]:
    path = Path(index_path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def rescan_image_assets(asset_root: str | Path, index_path: str | Path) -> list[dict[str, Any]]:
    root = Path(asset_root)
    assets = build_image_asset_index(root / "images")
    save_asset_index(assets, index_path)
    return assets


def search_assets(
    index_path: str | Path,
    query: str = "",
    category: str = "",
    kind: str = "image",
) -> list[dict[str, Any]]:
    q = query.strip()
    c = category.strip()
    result = [x for x in load_asset_index(index_path) if not kind or x.get("kind") == kind]
    if q:
        result = [
            x
            for x in result
            if q in (x.get("name") or "")
            or any(q in name for name in x.get("enterprise_names", []))
        ]
    if c:
        result = [x for x in result if c in (x.get("category") or "")]
    return result


def get_asset(index_path: str | Path, asset_id: str) -> dict[str, Any] | None:
    for asset in load_asset_index(index_path):
        if asset.get("asset_id") == asset_id:
            return asset
    return None
