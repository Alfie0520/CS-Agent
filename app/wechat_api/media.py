"""微信公众号临时素材上传。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.wechat_api.token_manager import token_manager


async def upload_temporary_media(file_path: str | Path, media_type: str = "image") -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        return {"errcode": -1, "errmsg": f"File not found: {path}"}

    token = await token_manager.get_token()
    settings = get_settings()
    url = f"{settings.wechat_api_base_url}/cgi-bin/media/upload?access_token={token}&type={media_type}"
    files = {"media": (path.name, path.read_bytes(), _mime_type(path))}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, files=files)
    return resp.json()


def _mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
