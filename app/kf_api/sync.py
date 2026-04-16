"""微信客服消息拉取：POST /cgi-bin/kf/sync_msg

微信客服的回调通知只是"有新消息"的信号，实际消息内容需要通过
sync_msg 接口主动拉取。cursor 用于增量拉取，需要持久化。
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from app.kf_api.client import kf_post

logger = logging.getLogger(__name__)

_SYNC_PATH = "/cgi-bin/kf/sync_msg"


class CursorStore:
    """持久化 sync_msg 的 next_cursor，防止进程重启后消息丢失或重复。"""

    def __init__(self, db_path: str = "data/kf_cursor.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS cursor_store "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.commit()

    def get(self, key: str = "default") -> str:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT value FROM cursor_store WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else ""

    def set(self, value: str, key: str = "default") -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO cursor_store (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            conn.commit()


_cursor_store = CursorStore()


async def sync_messages(
    token: str = "", open_kfid: str = "", limit: int = 1000
) -> dict[str, Any]:
    """拉取新消息。返回 {errcode, errmsg, next_cursor, has_more, msg_list}。

    Args:
        token: 回调通知中的 Token 字段（非 access_token），传入可提高频率上限。
        open_kfid: 指定拉取某个客服账号的消息，为空则拉取所有。
        limit: 单次拉取条数上限，默认 1000。
    """
    cursor = _cursor_store.get()
    payload: dict[str, Any] = {"cursor": cursor, "limit": limit}
    if token:
        payload["token"] = token
    if open_kfid:
        payload["open_kfid"] = open_kfid

    data = await kf_post(_SYNC_PATH, payload)

    if data.get("errcode", 0) == 0:
        next_cursor = data.get("next_cursor", "")
        if next_cursor:
            _cursor_store.set(next_cursor)

    return data
