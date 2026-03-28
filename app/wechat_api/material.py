"""微信永久素材管理：上传、列表等。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.wechat_api.token_manager import token_manager

_ADD_MATERIAL_PATH = "/cgi-bin/material/add_material"
_DEL_MATERIAL_PATH = "/cgi-bin/material/del_material"


async def add_material_image(file_path: str | Path) -> dict[str, Any]:
    """上传图片为永久素材。

    Args:
        file_path: 本地图片文件路径

    Returns:
        {"media_id": "xxx", "url": "https://..."} 或 {"errcode": ..., "errmsg": ...}
    """
    path = Path(file_path)
    if not path.exists():
        return {"errcode": -1, "errmsg": f"File not found: {path}"}

    token = await token_manager.get_token()
    settings = get_settings()
    url = f"{settings.wechat_api_base_url}{_ADD_MATERIAL_PATH}?access_token={token}&type=image"

    content = path.read_bytes()
    # 根据后缀推断 MIME（微信支持 bmp/png/jpeg/jpg/gif）
    suffix = path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".bmp": "image/bmp"}
    mime = mime_map.get(suffix, "image/jpeg")
    files = {"media": (path.name, content, mime)}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, files=files)
    return resp.json()


async def delete_material_image(media_id: str) -> dict[str, Any]:
    """从微信永久素材库删除图片。

    Args:
        media_id: 要删除的素材 media_id

    Returns:
        {"errcode": 0, "errmsg": "ok"} 或 {"errcode": ..., "errmsg": ...}
    """
    token = await token_manager.get_token()
    settings = get_settings()
    url = f"{settings.wechat_api_base_url}{_DEL_MATERIAL_PATH}?access_token={token}"
    payload = {"media_id": media_id}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload)
    return resp.json()
