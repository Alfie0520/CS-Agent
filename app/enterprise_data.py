"""企业参访数据加载与检索模块。

数据源优先使用运行时配置的 JSON，文件不存在时回退到代码内置
app/data/enterprises.json（由 scripts/build_enterprise_db.py 从 Excel 生成）。
查询时每次读取当前 JSON，避免业务数据更新依赖服务重启。
"""

from __future__ import annotations

import difflib
import json
import os
import re
from pathlib import Path
from typing import Any, TypedDict

from app.config import get_settings

_DATA_PATH = Path(__file__).parent / "data" / "enterprises.json"


class Enterprise(TypedDict):
    id: int
    city: str
    name: str
    themes: list[str]
    visit_experience: str
    sharing_topics: str
    core_value: str
    knowledge_points: str
    pain_points: str


_REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "id": int,
    "city": str,
    "name": str,
    "themes": list,
    "visit_experience": str,
    "sharing_topics": str,
    "core_value": str,
    "knowledge_points": str,
    "pain_points": str,
}


def get_data_path() -> Path:
    """获取运行时企业数据路径，配置文件不存在时回退到代码内置数据。"""
    configured = Path(get_settings().enterprise_data_path)
    return configured if configured.exists() else _DATA_PATH


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def load_enterprises() -> list[Enterprise]:
    """每次从当前 JSON 文件加载企业数据，避免业务数据更新依赖服务重启。"""
    with open(get_data_path(), encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save_enterprises(items: list[dict[str, Any]], path: str | Path | None = None) -> None:
    """原子写入企业数据 JSON。"""
    target = Path(path) if path else Path(get_settings().enterprise_data_path)
    _atomic_write_json(target, items)


def validate_enterprises(data: Any) -> list[dict[str, Any]]:
    """校验运行时企业 JSON，返回可保存的数据。"""
    if not isinstance(data, list):
        raise ValueError("Enterprise data must be a JSON array")
    seen_ids: set[int] = set()
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"row {index} must be an object")
        for field, expected_type in _REQUIRED_FIELDS.items():
            if field not in row:
                raise ValueError(f"row {index} missing required field: {field}")
            if not isinstance(row[field], expected_type):
                raise ValueError(f"row {index} field {field} must be {expected_type.__name__}")
        if row["id"] in seen_ids:
            raise ValueError(f"duplicate enterprise id: {row['id']}")
        seen_ids.add(row["id"])
        if not all(isinstance(theme, str) for theme in row["themes"]):
            raise ValueError(f"row {index} themes must be a list of strings")
    return data


# ---------- 内部匹配工具 ----------

def _norm(s: str) -> str:
    """统一小写、去空白，用于不区分大小写的比较。"""
    return s.lower().strip()


def _keyword_match(e: Enterprise, keyword: str) -> bool:
    kw = _norm(keyword)
    if kw in _norm(e["name"]):
        return True
    if kw in _norm(e["city"]):
        return True
    themes_str = "、".join(e.get("themes", []))
    if kw in _norm(themes_str):
        return True
    return False


def _fuzzy_match_names(
    enterprises: list[Enterprise], keyword: str, cutoff: float = 0.5
) -> list[int]:
    """用 difflib 对企业名做模糊匹配，返回命中的企业 id 列表。"""
    all_names = [e["name"] for e in enterprises]
    matches = difflib.get_close_matches(keyword, all_names, n=10, cutoff=cutoff)
    return [e["id"] for e in enterprises if e["name"] in matches]


# ---------- 公开 API ----------

def search_overview(
    city: str = "",
    keyword: str = "",
    themes: list[str] | None = None,
    limit: int = 30,
) -> list[dict]:
    """
    搜索企业参访方案概览（仅返回 id、城市、企业名、主题标签）。

    过滤逻辑（多个条件之间为 AND）：
    - city: 城市字段包含该子串即命中（如 "深圳"、"浙江"）
    - keyword: 企业名 / 城市 / 主题标签中包含该关键词即命中；若无精确命中，自动
      对企业名做模糊匹配兜底
    - themes: 企业至少匹配其中一个主题标签即命中（OR 关系）
    - limit: 最多返回条数，默认 30

    返回列表，每项包含 id、city、name、themes。
    """
    enterprises = load_enterprises()
    candidates = list(enterprises)

    # 城市过滤（子串匹配）
    if city:
        candidates = [e for e in candidates if city in e["city"]]

    # 主题标签过滤（任意一个命中即可）
    if themes:
        norm_themes = [_norm(t) for t in themes]
        candidates = [
            e for e in candidates
            if any(_norm(tag) in norm_themes or any(nt in _norm(tag) for nt in norm_themes)
                   for tag in e.get("themes", []))
        ]

    # 关键字过滤（精确子串匹配）
    if keyword:
        matched = [e for e in candidates if _keyword_match(e, keyword)]
        # 无精确命中时，对企业名做模糊兜底
        if not matched:
            fuzzy_ids = set(_fuzzy_match_names(enterprises, keyword))
            matched = [e for e in candidates if e["id"] in fuzzy_ids]
        candidates = matched

    # 截断
    candidates = candidates[:limit]

    return [
        {"id": e["id"], "city": e["city"], "name": e["name"], "themes": e["themes"]}
        for e in candidates
    ]


def get_detail(
    names: list[str] | None = None,
    ids: list[int] | None = None,
    fuzzy: bool = False,
) -> list[Enterprise]:
    """
    按企业名或 id 获取完整参访方案详情，支持批量查询。

    - names: 企业名列表，默认做子串匹配；fuzzy=True 时退回到编辑距离模糊匹配
    - ids: 企业 id 列表，精确命中
    - fuzzy: 仅对 names 生效，开启后对未命中的名称尝试模糊匹配

    两个参数可同时传入，结果取并集去重。
    """
    enterprises = load_enterprises()
    id_index = {e["id"]: e for e in enterprises}

    result_ids: set[int] = set()

    if ids:
        for eid in ids:
            if eid in id_index:
                result_ids.add(eid)

    if names:
        for name in names:
            norm_name = _norm(name)
            # 先做子串匹配
            exact = [e["id"] for e in enterprises if norm_name in _norm(e["name"])]
            if exact:
                result_ids.update(exact)
            elif fuzzy:
                fuzzy_ids = _fuzzy_match_names(enterprises, name, cutoff=0.4)
                result_ids.update(fuzzy_ids)

    # 保持原数据顺序
    return [id_index[eid] for eid in sorted(result_ids) if eid in id_index]


# ---------- 格式化输出（供 tool 返回给 LLM 使用）----------

def fmt_overview(items: list[dict]) -> str:
    if not items:
        return "未找到匹配的参访方案。"
    lines = [f"共找到 {len(items)} 个参访方案（概览）：\n"]
    for e in items:
        themes_str = "、".join(e["themes"]) if e["themes"] else "—"
        lines.append(f"[{e['id']}] {e['city']} | {e['name']}")
        lines.append(f"    主题：{themes_str}")
    return "\n".join(lines)


def fmt_detail(items: list[Enterprise]) -> str:
    if not items:
        return "未找到对应的企业参访方案。"
    parts = []
    for e in items:
        themes_str = "、".join(e["themes"]) if e["themes"] else "—"
        block = [
            f"{'=' * 50}",
            f"【{e['name']}】（{e['city']}）  编号：{e['id']}",
            f"{'=' * 50}",
            f"主题方向：{themes_str}",
            "",
            f"▌参观体验\n{e['visit_experience'] or '—'}",
            "",
            f"▌主题分享\n{e['sharing_topics'] or '—'}",
            "",
            f"▌研学核心价值\n{e['core_value'] or '—'}",
            "",
            f"▌能够赋能企业的知识点\n{e['knowledge_points'] or '—'}",
            "",
            f"▌能够解决客户的业务及管理痛点\n{e['pain_points'] or '—'}",
        ]
        parts.append("\n".join(block))
    return "\n\n".join(parts)
