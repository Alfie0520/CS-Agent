"""微信客服 API HTTP 客户端，自动注入 KF access_token。"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings
from app.kf_api.token_manager import kf_token_manager

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=10)
    return _client


async def kf_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """向微信客服 API 发送 POST 请求。"""
    settings = get_settings()
    token = await kf_token_manager.get_token()
    url = f"{settings.kf_api_base_url}{path}?access_token={token}"
    client = _get_client()
    resp = await client.post(url, json=payload)
    data = resp.json()
    if data.get("errcode", 0) != 0:
        logger.error("KF API error: %s %s -> %s", path, payload, data)
    return data


async def kf_get(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    """向微信客服 API 发送 GET 请求。"""
    settings = get_settings()
    token = await kf_token_manager.get_token()
    query: dict[str, str] = {"access_token": token}
    if params:
        query.update(params)
    url = f"{settings.kf_api_base_url}{path}"
    client = _get_client()
    resp = await client.get(url, params=query)
    return resp.json()
