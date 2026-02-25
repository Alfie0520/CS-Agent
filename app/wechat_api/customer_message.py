"""封装微信客服消息发送接口：POST /cgi-bin/message/custom/send"""

from __future__ import annotations

import logging
from typing import Any

from app.wechat_api.client import wechat_post

logger = logging.getLogger(__name__)

_SEND_PATH = "/cgi-bin/message/custom/send"


async def _send(payload: dict[str, Any]) -> dict[str, Any]:
    return await wechat_post(_SEND_PATH, payload)


async def send_text(
    openid: str, content: str, *, ai_msg: bool = False
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "touser": openid,
        "msgtype": "text",
        "text": {"content": content},
    }
    if ai_msg:
        payload["aimsgcontext"] = {"is_ai_msg": 1}
    return await _send(payload)


async def send_image(openid: str, media_id: str) -> dict[str, Any]:
    return await _send(
        {
            "touser": openid,
            "msgtype": "image",
            "image": {"media_id": media_id},
        }
    )


async def send_menu(
    openid: str,
    head: str,
    items: list[dict[str, str]],
    tail: str = "",
) -> dict[str, Any]:
    """发送菜单消息。items 格式: [{"id": "101", "content": "满意"}, ...]"""
    return await _send(
        {
            "touser": openid,
            "msgtype": "msgmenu",
            "msgmenu": {
                "head_content": head,
                "list": items,
                "tail_content": tail,
            },
        }
    )


async def send_news(
    openid: str,
    title: str,
    description: str,
    url: str,
    pic_url: str,
) -> dict[str, Any]:
    return await _send(
        {
            "touser": openid,
            "msgtype": "news",
            "news": {
                "articles": [
                    {
                        "title": title,
                        "description": description,
                        "url": url,
                        "picurl": pic_url,
                    }
                ]
            },
        }
    )
