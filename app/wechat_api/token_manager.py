from __future__ import annotations

import asyncio
import logging
import time

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_REFRESH_BUFFER_SECONDS = 300  # 提前 5 分钟刷新


class TokenManager:
    """Access Token 生命周期管理：启动时获取，定时自动刷新，提供 get_token() 供业务调用。"""

    def __init__(self) -> None:
        self._token: str = ""
        self._expires_at: float = 0
        self._refresh_task: asyncio.Task | None = None
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=10)
        await self._fetch_token()
        self._refresh_task = asyncio.create_task(self._auto_refresh_loop())

    async def stop(self) -> None:
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()

    async def get_token(self) -> str:
        if time.time() >= self._expires_at:
            await self._fetch_token()
        return self._token

    async def _fetch_token(self) -> None:
        settings = get_settings()
        url = (
            f"{settings.wechat_api_base_url}/cgi-bin/token"
            f"?grant_type=client_credential"
            f"&appid={settings.wechat_app_id}"
            f"&secret={settings.wechat_app_secret}"
        )
        try:
            resp = await self._client.get(url)
            data = resp.json()
            if "access_token" in data:
                self._token = data["access_token"]
                expires_in = data.get("expires_in", 7200)
                self._expires_at = time.time() + expires_in - _REFRESH_BUFFER_SECONDS
                logger.info("Access token refreshed, expires_in=%s", expires_in)
            else:
                logger.error("Failed to get access token: %s", data)
        except Exception:
            logger.exception("Error fetching access token")

    async def _auto_refresh_loop(self) -> None:
        """每隔 (expires_in - buffer) 秒自动刷新 token。"""
        while True:
            sleep_seconds = max(self._expires_at - time.time(), 60)
            await asyncio.sleep(sleep_seconds)
            await self._fetch_token()


token_manager = TokenManager()
