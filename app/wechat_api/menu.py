"""封装微信自定义菜单相关接口：创建/查询/删除/个性化菜单"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.wechat_api.client import wechat_get, wechat_post

logger = logging.getLogger(__name__)

_CREATE_PATH = "/cgi-bin/menu/create"
_GET_PATH = "/cgi-bin/menu/get"
_DELETE_PATH = "/cgi-bin/menu/delete"
_GET_CURRENT_PATH = "/cgi-bin/get_current_selfmenu_info"
_ADD_CONDITIONAL_PATH = "/cgi-bin/menu/addconditional"
_DEL_CONDITIONAL_PATH = "/cgi-bin/menu/delconditional"
_TRY_MATCH_PATH = "/cgi-bin/menu/trymatch"


async def create_menu(menu_data: dict[str, Any]) -> dict[str, Any]:
    """创建自定义菜单。

    注意：完全匹配微信官方接口格式，button 数组最多 3 个一级菜单，
    每个一级菜单下最多 5 个子菜单。
    """
    return await wechat_post(_CREATE_PATH, menu_data)


async def get_menu() -> dict[str, Any]:
    """查询自定义菜单配置。"""
    return await wechat_get(_GET_PATH)


async def delete_menu() -> dict[str, Any]:
    """删除当前使用的自定义菜单。"""
    return await wechat_get(_DELETE_PATH)


async def get_current_selfmenu_info() -> dict[str, Any]:
    """获取当前使用的自定义菜单配置。"""
    return await wechat_get(_GET_CURRENT_PATH)


async def add_conditional_menu(menu_data: dict[str, Any]) -> dict[str, Any]:
    """创建个性化菜单。"""
    return await wechat_post(_ADD_CONDITIONAL_PATH, menu_data)


async def del_conditional_menu(menuid: str) -> dict[str, Any]:
    """删除指定个性化菜单。"""
    return await wechat_post(_DEL_CONDITIONAL_PATH, {"menuid": menuid})


async def try_match_menu(user_id: str) -> dict[str, Any]:
    """测试个性化菜单匹配结果。

    Args:
        user_id: 微信号（OpenID 或 绑定指定 UID 的微信号）
    """
    return await wechat_post(_TRY_MATCH_PATH, {"user_id": user_id})


async def create_menu_from_json_file(file_path: str) -> dict[str, Any]:
    """从本地 JSON 文件加载菜单配置并创建。

    Args:
        file_path: 菜单 JSON 文件路径
    """
    path = Path(file_path)
    if not path.exists():
        return {"errcode": 40013, "errmsg": f"Menu file not found: {file_path}"}
    try:
        menu_data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Failed to read menu JSON from %s: %s", file_path, e)
        return {"errcode": 40013, "errmsg": f"Invalid JSON: {e}"}
    return await create_menu(menu_data)
