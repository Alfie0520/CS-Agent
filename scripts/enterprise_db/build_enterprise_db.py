#!/usr/bin/env python3
"""将 data/2026游学资源表.xlsx 转换为 app/data/enterprises.json。

用法：
    cd /path/to/CS-Agent
    python scripts/enterprise_db/build_enterprise_db.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("请先安装 openpyxl：pip install openpyxl")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
EXCEL_PATH = SCRIPT_DIR / "data" / "2026游学资源表.xlsx"
OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "app" / "data" / "enterprises.json"


def parse_themes(raw: str | None) -> list[str]:
    if not raw:
        return []
    tags = re.split(r"[、，,\s]+", str(raw).strip())
    seen: set[str] = set()
    result = []
    for t in tags:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            result.append(t)
    return result


def clean(value) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return "" if s == "None" else s


def main() -> None:
    if not EXCEL_PATH.exists():
        print(f"找不到文件：{EXCEL_PATH}")
        sys.exit(1)

    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb["标杆企业"]
    all_rows = list(ws.iter_rows(values_only=True))

    data_rows = [r for r in all_rows[2:] if any(c for c in r)]

    enterprises = []
    for row in data_rows:
        if not row[0] or not row[3]:
            continue
        themes = parse_themes(clean(row[4]))
        entry = {
            "id": int(row[0]) if str(row[0]).isdigit() else row[0],
            "city": clean(row[2]),
            "name": clean(row[3]),
            "themes": themes,
            "visit_experience": clean(row[5]),
            "sharing_topics": clean(row[6]),
            "core_value": clean(row[7]),
            "knowledge_points": clean(row[8]),
            "pain_points": clean(row[9]),
        }
        enterprises.append(entry)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(enterprises, f, ensure_ascii=False, indent=2)

    print(f"完成：共写入 {len(enterprises)} 条企业数据 → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()