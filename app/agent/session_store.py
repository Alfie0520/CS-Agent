"""按 openid 管理多轮对话历史，纯内存实现，带 TTL 自动过期。"""

from __future__ import annotations

import time
from typing import Any


class SessionStore:
    """存储每个用户（openid）的 pydantic-ai 消息历史。

    - history: list[ModelMessage]，直接传给 agent.run(message_history=...)
    - 超过 ttl 秒未活跃则清空，避免无限增长
    """

    def __init__(self, ttl: int = 1800) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[list[Any], float]] = {}  # openid -> (messages, last_active)

    def get(self, openid: str) -> list[Any]:
        entry = self._store.get(openid)
        if entry is None:
            return []
        messages, last_active = entry
        if time.time() - last_active > self._ttl:
            del self._store[openid]
            return []
        return messages

    def set(self, openid: str, messages: list[Any]) -> None:
        self._store[openid] = (messages, time.time())

    def clear(self, openid: str) -> None:
        self._store.pop(openid, None)
