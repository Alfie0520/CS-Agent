"""微信客服渠道适配器。"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class KfChannelAdapter:
    """微信客服渠道适配器。

    Phase 2 仅支持文本消息收发，图片/菜单等暂做降级处理。
    """

    channel_name: str = "kf"

    def __init__(self, open_kfid: str) -> None:
        self._open_kfid = open_kfid

    async def send_text(self, user_id: str, content: str) -> dict[str, Any]:
        from app.kf_api import messaging
        return await messaging.send_text(user_id, self._open_kfid, content)

    async def send_image(self, user_id: str, media_id: str) -> dict[str, Any]:
        # Phase 2 暂不支持图片，降级为文字提示
        logger.info("KF send_image skipped (not supported yet): user=%s", user_id)
        return {"errcode": 0, "errmsg": "image not supported in KF channel yet"}

    async def send_menu(
        self,
        user_id: str,
        head: str,
        items: list[dict[str, str]],
        tail: str,
    ) -> dict[str, Any]:
        # 菜单消息降级为纯文本
        parts = [head]
        for item in items:
            parts.append(f"- {item.get('content', '')}")
        if tail:
            parts.append(tail)
        text = "\n".join(parts)
        return await self.send_text(user_id, text)

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        from app.kf_api.client import kf_post
        data = await kf_post(
            "/cgi-bin/kf/customer/batchget",
            {"external_userid_list": [user_id]},
        )
        customers = data.get("customer_list", [])
        if customers:
            c = customers[0]
            return {
                "subscribe": 1,
                "nickname": c.get("nickname", ""),
                "avatar": c.get("avatar", ""),
                "gender": c.get("gender", 0),
            }
        return {"subscribe": 0}

    async def api_get(
        self, path: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        # 服务号专属 API 在客服渠道不可用
        return {"errcode": -1, "errmsg": "API not available on KF channel"}

    async def api_post(
        self, path: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {"errcode": -1, "errmsg": "API not available on KF channel"}
