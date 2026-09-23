"""内部资产管理 API。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Header, Query, UploadFile

from app.assets.index import (
    _IMAGE_SUFFIXES,
    get_asset,
    load_asset_index,
    rescan_image_assets,
    search_assets,
)
from app.config import get_settings

router = APIRouter(prefix="/api/assets", tags=["assets"])

logger = logging.getLogger(__name__)


def _check_api_key(api_key: str | None, x_api_key: str | None = None) -> dict[str, Any] | None:
    expected_key = get_settings().visit_image_api_key
    provided_key = api_key or x_api_key
    if expected_key and provided_key != expected_key:
        return {"success": False, "error": "Invalid API key"}
    return None


def _asset_paths() -> tuple[Path, Path]:
    settings = get_settings()
    return Path(settings.asset_root_path), Path(settings.asset_index_path)


def _safe_category(category: str) -> Path:
    category_path = Path(category.strip())
    if category_path.is_absolute() or ".." in category_path.parts:
        raise ValueError("Invalid category")
    return category_path


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_bytes(content)
    os.replace(tmp_path, path)


def _remove_shadowing_siblings(category_dir: Path, filename: str) -> list[str]:
    """删除同目录下「同名不同后缀」的旧文件。

    资产索引用 (category, 文件名主干) 生成 asset_id，若 `联想.jpg` 与 `联想.png`
    并存，索引里会出现两条相同 asset_id 的记录，而 get_asset 只取排序后的第一条
    （.jpg 排在 .png 前），导致刚上传的新图取不到。上传新图时清掉旧后缀即可。
    """
    stem = Path(filename).stem
    removed: list[str] = []
    for sibling in sorted(category_dir.iterdir()):
        if not sibling.is_file() or sibling.name == filename:
            continue
        if sibling.stem == stem and sibling.suffix.lower() in _IMAGE_SUFFIXES:
            sibling.unlink()
            removed.append(sibling.name)
            logger.info("asset_upsert removed_shadowing file=%s", sibling)
    return removed


@router.get("")
async def list_assets(
    kind: str = Query("image"),
    api_key: str | None = Query(None),
    x_api_key: str | None = Header(None),
) -> dict[str, Any]:
    error = _check_api_key(api_key, x_api_key)
    if error:
        return error
    _, index_path = _asset_paths()
    items = [x for x in load_asset_index(index_path) if not kind or x.get("kind") == kind]
    return {"success": True, "count": len(items), "items": items}


@router.get("/search")
async def search_asset_api(
    query: str = Query(""),
    category: str = Query(""),
    kind: str = Query("image"),
    api_key: str | None = Query(None),
    x_api_key: str | None = Header(None),
) -> dict[str, Any]:
    error = _check_api_key(api_key, x_api_key)
    if error:
        return error
    _, index_path = _asset_paths()
    items = search_assets(index_path, query=query, category=category, kind=kind)
    return {"success": True, "count": len(items), "items": items}


@router.get("/stats")
async def asset_stats_api(
    kind: str = Query("image"),
    api_key: str | None = Query(None),
    x_api_key: str | None = Header(None),
) -> dict[str, Any]:
    error = _check_api_key(api_key, x_api_key)
    if error:
        return error
    _, index_path = _asset_paths()
    items = [x for x in load_asset_index(index_path) if not kind or x.get("kind") == kind]
    categories: dict[str, int] = {}
    for item in items:
        category = item.get("category") or ""
        categories[category] = categories.get(category, 0) + 1
    return {
        "success": True,
        "count": len(items),
        "categories": dict(sorted(categories.items())),
    }


@router.post("/rescan")
async def rescan_assets_api(
    api_key: str | None = Form(None),
    x_api_key: str | None = Header(None),
) -> dict[str, Any]:
    error = _check_api_key(api_key, x_api_key)
    if error:
        return error
    asset_root, index_path = _asset_paths()
    items = rescan_image_assets(asset_root, index_path)
    return {"success": True, "count": len(items)}


@router.post("/image")
async def upsert_image_asset_api(
    image_file: UploadFile = File(...),
    category: str = Form(...),
    image_name: str | None = Form(None),
    api_key: str | None = Form(None),
    x_api_key: str | None = Header(None),
) -> dict[str, Any]:
    error = _check_api_key(api_key, x_api_key)
    if error:
        return error

    try:
        category_path = _safe_category(category)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    filename = image_name or image_file.filename
    if not filename:
        return {"success": False, "error": "image_name or upload filename is required"}
    if Path(filename).name != filename:
        return {"success": False, "error": "image_name must not contain path separators"}
    if Path(filename).suffix.lower() not in _IMAGE_SUFFIXES:
        return {"success": False, "error": f"Unsupported image suffix: {Path(filename).suffix}"}

    content = await image_file.read()
    if not content:
        return {"success": False, "error": "image file is empty"}

    asset_root, index_path = _asset_paths()
    category_dir = asset_root / "images" / category_path
    target = category_dir / filename
    _atomic_write_bytes(target, content)
    removed = _remove_shadowing_siblings(category_dir, filename)
    items = rescan_image_assets(asset_root, index_path)
    asset = next((x for x in items if Path(x.get("path", "")).name == filename and x.get("category") == category_path.as_posix()), None)
    return {"success": True, "count": len(items), "asset": asset, "removed_shadowing": removed}


@router.get("/{asset_id:path}")
async def get_asset_api(
    asset_id: str,
    api_key: str | None = Query(None),
    x_api_key: str | None = Header(None),
) -> dict[str, Any]:
    error = _check_api_key(api_key, x_api_key)
    if error:
        return error

    asset_root, index_path = _asset_paths()
    asset = get_asset(index_path, asset_id)
    if not asset:
        return {"success": False, "error": f"Asset not found: {asset_id}"}

    target = (asset_root / asset["path"]).resolve()
    try:
        target.relative_to(asset_root.resolve())
    except ValueError:
        return {"success": False, "error": "Asset path escapes asset root"}
    return {
        "success": True,
        "asset": asset,
        "exists": target.exists(),
        "size": target.stat().st_size if target.exists() else 0,
    }


@router.delete("/{asset_id:path}")
async def delete_asset_api(
    asset_id: str,
    api_key: str | None = Query(None),
    x_api_key: str | None = Header(None),
) -> dict[str, Any]:
    error = _check_api_key(api_key, x_api_key)
    if error:
        return error

    asset_root, index_path = _asset_paths()
    asset = get_asset(index_path, asset_id)
    if not asset:
        return {"success": False, "error": f"Asset not found: {asset_id}"}

    target = (asset_root / asset["path"]).resolve()
    try:
        target.relative_to(asset_root.resolve())
    except ValueError:
        return {"success": False, "error": "Asset path escapes asset root"}

    target.unlink(missing_ok=True)
    items = rescan_image_assets(asset_root, index_path)
    return {"success": True, "count": len(items), "deleted": asset}
