"""发送业务资产到不同微信渠道。"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.assets.index import get_asset
from app.channel.base import ChannelAdapter

UploadMedia = Callable[[str, Path, str], Awaitable[dict[str, Any]]]

logger = logging.getLogger(__name__)


async def default_upload_media(
    channel_name: str, file_path: Path, media_type: str
) -> dict[str, Any]:
    if channel_name == "kf":
        from app.kf_api.media import upload_temporary_media

        return await upload_temporary_media(file_path, media_type)

    if channel_name == "official_account":
        from app.wechat_api.media import upload_temporary_media

        return await upload_temporary_media(file_path, media_type)

    raise ValueError(f"Unsupported channel for asset delivery: {channel_name}")


class AssetDeliveryService:
    def __init__(
        self,
        asset_root: str | Path,
        index_path: str | Path,
        cache_path: str | Path,
        upload_media: UploadMedia = default_upload_media,
    ) -> None:
        self.asset_root = Path(asset_root)
        self.index_path = Path(index_path)
        self.cache_path = Path(cache_path)
        self.upload_media = upload_media

    async def send_asset(
        self, channel: ChannelAdapter, user_id: str, asset_id: str
    ) -> dict[str, Any]:
        started = time.perf_counter()
        asset = get_asset(self.index_path, asset_id)
        if not asset:
            return {"errcode": -1, "errmsg": f"Asset not found: {asset_id}"}
        if asset.get("kind") != "image":
            return {"errcode": -1, "errmsg": f"Unsupported asset kind: {asset.get('kind')}"}

        file_path = self._resolve_asset_path(asset["path"])
        media_id = await self._get_or_upload_media(channel.channel_name, asset, file_path)
        send_started = time.perf_counter()
        result = await channel.send_image(user_id, media_id)
        logger.info(
            "asset_delivery send_done channel=%s asset_id=%s elapsed_ms=%.1f total_ms=%.1f errcode=%s",
            channel.channel_name,
            asset_id,
            (time.perf_counter() - send_started) * 1000,
            (time.perf_counter() - started) * 1000,
            result.get("errcode"),
        )
        return result

    def _resolve_asset_path(self, rel_path: str) -> Path:
        root = self.asset_root.resolve()
        target = (root / rel_path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            raise ValueError(f"Asset path escapes asset root: {rel_path}")
        if not target.exists():
            raise FileNotFoundError(target)
        return target

    async def _get_or_upload_media(
        self, channel_name: str, asset: dict[str, Any], file_path: Path
    ) -> str:
        media_type = "image"
        cached = self._find_valid_cache(channel_name, asset["asset_id"], asset["sha256"], media_type)
        if cached:
            logger.info(
                "asset_delivery cache_hit channel=%s asset_id=%s expires_at=%s",
                channel_name,
                asset["asset_id"],
                cached.get("expires_at"),
            )
            return cached["media_id"]

        started = time.perf_counter()
        result = await self.upload_media(channel_name, file_path, media_type)
        media_id = result.get("media_id")
        if not media_id:
            raise RuntimeError(f"Media upload failed: {result}")
        logger.info(
            "asset_delivery upload_done channel=%s asset_id=%s bytes=%s elapsed_ms=%.1f",
            channel_name,
            asset["asset_id"],
            file_path.stat().st_size,
            (time.perf_counter() - started) * 1000,
        )

        expires_in = int(result.get("expires_in") or 259200)
        self._upsert_cache(
            {
                "asset_id": asset["asset_id"],
                "sha256": asset["sha256"],
                "channel": channel_name,
                "media_type": media_type,
                "media_id": media_id,
                "expires_at": int(time.time()) + expires_in,
            }
        )
        return media_id

    def _load_cache(self) -> list[dict[str, Any]]:
        if not self.cache_path.exists():
            return []
        data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _save_cache(self, cache: list[dict[str, Any]]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.cache_path.with_name(f".{self.cache_path.name}.tmp")
        tmp_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, self.cache_path)

    def _find_valid_cache(
        self, channel: str, asset_id: str, sha256: str, media_type: str
    ) -> dict[str, Any] | None:
        now = int(time.time())
        for item in self._load_cache():
            if (
                item.get("channel") == channel
                and item.get("asset_id") == asset_id
                and item.get("sha256") == sha256
                and item.get("media_type") == media_type
                and int(item.get("expires_at", 0)) > now + 60
            ):
                return item
        return None

    def _upsert_cache(self, new_item: dict[str, Any]) -> None:
        cache = [
            item
            for item in self._load_cache()
            if not (
                item.get("channel") == new_item["channel"]
                and item.get("asset_id") == new_item["asset_id"]
                and item.get("media_type") == new_item["media_type"]
            )
        ]
        cache.append(new_item)
        self._save_cache(cache)
