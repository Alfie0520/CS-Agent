"""渠道适配器抽象：定义多渠道消息收发的统一接口。"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChannelAdapter(Protocol):
    """消息渠道适配器协议。

    每个渠道（服务号、微信客服等）实现此协议，
    Agent 核心通过此接口与具体渠道交互，实现解耦。
    """

    channel_name: str

    async def send_text(self, user_id: str, content: str) -> dict[str, Any]:
        """发送文本消息。"""
        ...

    async def send_image(self, user_id: str, media_id: str) -> dict[str, Any]:
        """发送图片消息。"""
        ...

    async def send_menu(
        self,
        user_id: str,
        head: str,
        items: list[dict[str, str]],
        tail: str,
    ) -> dict[str, Any]:
        """发送菜单消息。"""
        ...

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """查询用户信息。"""
        ...

    async def api_get(
        self, path: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """通用 GET 请求（供渠道专属 API 调用）。"""
        ...

    async def api_post(
        self, path: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """通用 POST 请求（供渠道专属 API 调用）。"""
        ...
