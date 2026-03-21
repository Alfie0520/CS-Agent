"""按 openid 管理多轮对话历史，SQLite 持久化存储。"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter
from pydantic_ai.messages import ModelMessage

logger = logging.getLogger(__name__)

_ta: TypeAdapter[list[ModelMessage]] = TypeAdapter(list[ModelMessage])


class SessionStore:
    """存储每个用户（openid）的 pydantic-ai 消息历史，持久化到 SQLite。

    - ttl=0 表示永不过期；ttl>0 表示超过该秒数未活跃则清空上下文
    """

    def __init__(self, db_path: str = "data/sessions.db", ttl: int = 0) -> None:
        self._db_path = db_path
        self._ttl = ttl
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    openid      TEXT PRIMARY KEY,
                    messages    BLOB NOT NULL,
                    updated_at  REAL NOT NULL
                )
            """)
            conn.commit()

    # ---------- 同步实现（在线程池中执行）----------

    def _get_sync(self, openid: str) -> list[Any]:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT messages, updated_at FROM sessions WHERE openid = ?",
                (openid,),
            ).fetchone()
        if row is None:
            return []
        messages_bytes, updated_at = row
        if self._ttl > 0 and time.time() - updated_at > self._ttl:
            return []
        try:
            return _ta.validate_json(messages_bytes)
        except Exception:
            logger.warning("Failed to deserialize session for %s, resetting", openid)
            return []

    def _set_sync(self, openid: str, messages: list[Any]) -> None:
        messages_bytes = _ta.dump_json(messages)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO sessions (openid, messages, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(openid) DO UPDATE SET
                    messages   = excluded.messages,
                    updated_at = excluded.updated_at
                """,
                (openid, messages_bytes, time.time()),
            )
            conn.commit()

    def _clear_sync(self, openid: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE openid = ?", (openid,))
            conn.commit()

    # ---------- 异步接口 ----------

    async def get(self, openid: str) -> list[Any]:
        return await asyncio.to_thread(self._get_sync, openid)

    async def set(self, openid: str, messages: list[Any]) -> None:
        await asyncio.to_thread(self._set_sync, openid, messages)

    async def clear(self, openid: str) -> None:
        await asyncio.to_thread(self._clear_sync, openid)
