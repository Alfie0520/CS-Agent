#!/usr/bin/env python3
"""将 data/media_index.db 迁移到 media_index.json（一次性）。"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.media_index import get_index_path, save_items

_DB_PATH = Path("data/media_index.db")


def main() -> None:
    if not _DB_PATH.exists():
        print(f"未找到 {_DB_PATH}，无需迁移。")
        return
    conn = sqlite3.connect(_DB_PATH)
    cur = conn.execute("SELECT media_id, image_name, category FROM media_index")
    rows = cur.fetchall()
    conn.close()
    items = [{"media_id": r[0], "image_name": r[1], "category": r[2]} for r in rows]
    save_items(items)
    print(f"已迁移 {len(items)} 条记录到 {get_index_path()}")
