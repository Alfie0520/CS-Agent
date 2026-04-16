"""服务号渠道适配器：包装现有 wechat_api 模块，实现 ChannelAdapter 协议。"""

from __future__ import annotations

from typing import Any


class OfficialAccountAdapter:
    """微信服务号渠道适配器。"""

    channel_name: str = "official_account"

    async def send_text(self, user_id: str, content: str) -> dict[str, Any]:
        from app.wechat_api import customer_message
        return await customer_message.send_text(user_id, content)

    async def send_image(self, user_id: str, media_id: str) -> dict[str, Any]:
        from app.wechat_api import customer_message
        return await customer_message.send_image(user_id, media_id)

    async def send_menu(
        self,
        user_id: str,
        head: str,
        items: list[dict[str, str]],
        tail: str,
    ) -> dict[str, Any]:
        from app.wechat_api import customer_message
        return await customer_message.send_menu(user_id, head, items, tail)

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        from app.wechat_api.client import wechat_get
        return await wechat_get(
            "/cgi-bin/user/info", {"openid": user_id, "lang": "zh_CN"}
        )

    async def api_get(
        self, path: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        from app.wechat_api.client import wechat_get
        return await wechat_get(path, params)

    async def api_post(
        self, path: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        from app.wechat_api.client import wechat_post
        return await wechat_post(path, payload)
