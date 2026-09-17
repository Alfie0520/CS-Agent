"""微信客服临时素材上传。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.kf_api.token_manager import kf_token_manager


async def upload_temporary_media(file_path: str | Path, media_type: str = "image") -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        return {"errcode": -1, "errmsg": f"File not found: {path}"}

    token = await kf_token_manager.get_token()
    settings = get_settings()
    url = f"{settings.kf_api_base_url}/cgi-bin/media/upload?access_token={token}&type={media_type}"
    files = {"media": (path.name, path.read_bytes(), _mime_type(path))}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, files=files)
    return resp.json()


async def download_temporary_media(media_id: str, dest_path: str | Path) -> dict[str, Any]:
    """下载微信客服临时素材到本地文件。

    出错时接口返回 JSON，先看 Content-Type：是 JSON 就当作错误直接返回，不落盘。
    """
    token = await kf_token_manager.get_token()
    settings = get_settings()
    url = f"{settings.kf_api_base_url}/cgi-bin/media/get"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            url, params={"access_token": token, "media_id": media_id}
        )

    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type or "text/plain" in content_type:
        try:
            return resp.json()
        except ValueError:
            return {"errcode": -1, "errmsg": resp.text[:200]}

    path = Path(dest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(resp.content)
    return {"errcode": 0, "errmsg": "ok", "path": str(path), "size": len(resp.content)}


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
