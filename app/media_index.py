"""参访方案图片索引：media_id、图片名称、分类的映射，JSON 存储。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def get_index_path() -> Path:
    """索引文件路径，位于 data/ 目录下，不随代码提交。"""
    return Path("data/media_index.json")


def _load() -> list[dict[str, str]]:
    """加载索引，返回 [{"media_id", "image_name", "category"}, ...]。"""
    path = get_index_path()
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    return data if isinstance(data, list) else []


def _save(items: list[dict[str, str]]) -> None:
    """保存索引。"""
    path = get_index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def save_items(items: list[dict[str, str]]) -> None:
    """批量保存索引（供迁移等使用）。"""
    _save(items)


def upsert(media_id: str, image_name: str, category: str) -> None:
    """插入或更新一条记录（按 category + image_name 去重）。"""
    items = _load()
    key = (category, image_name)
    items = [x for x in items if (x.get("category"), x.get("image_name")) != key]
    items.append({"media_id": media_id, "image_name": image_name, "category": category})
    _save(items)


def get_overview() -> dict[str, Any]:
    """获取概览：分类（文件夹=地理位置）及每个分类下的方案数量。

    Returns:
        {"total": int, "categories": {"分类名": 数量, ...}}
    """
    items = _load()
    cats: dict[str, int] = {}
    for x in items:
        c = x.get("category", "")
        cats[c] = cats.get(c, 0) + 1
    return {"total": len(items), "categories": dict(sorted(cats.items()))}


def list_schemes(category: str | None = None) -> list[dict[str, str]]:
    """按分类列出方案，category 为空则返回全部。

    Returns:
        [{"media_id", "image_name", "category"}, ...]
    """
    items = _load()
    if category:
        items = [x for x in items if x.get("category") == category]
    return items


def search(keyword: str) -> list[dict[str, str]]:
    """按关键词模糊搜索（匹配分类或图片名称）。

    Returns:
        [{"media_id", "image_name", "category"}, ...]
    """
    items = _load()
    kw = keyword.strip()
    if not kw:
        return []
    return [
        x
        for x in items
        if kw in (x.get("category") or "") or kw in (x.get("image_name") or "")
    ]


def exists(category: str, image_name: str) -> bool:
    """检查 (category, image_name) 是否已存在，用于增量上传。"""
    items = _load()
    return any(
        x.get("category") == category and x.get("image_name") == image_name
        for x in items
    )


def get_by_media_id(media_id: str) -> dict[str, str] | None:
    """根据 media_id 查询单条记录。"""
    items = _load()
    for x in items:
        if x.get("media_id") == media_id:
            return x
    return None


def delete(media_id: str) -> bool:
    """根据 media_id 删除一条记录，返回是否删除成功。"""
    items = _load()
    original_len = len(items)
    items = [x for x in items if x.get("media_id") != media_id]
    if len(items) < original_len:
        _save(items)
        return True
    return False
