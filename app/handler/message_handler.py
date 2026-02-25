"""普通消息处理：调用 Agent 生成回复，通过客服消息接口发送。"""

from __future__ import annotations

import logging

from app.agent.base import BaseAgent
from app.models.message import IncomingMessage
from app.wechat_api import customer_message

logger = logging.getLogger(__name__)


async def handle_message(msg: IncomingMessage, agent: BaseAgent) -> None:
    response = await agent.handle(msg)

    if not response.replies:
        return

    for reply in response.replies:
        try:
            if reply.msg_type == "text" and reply.text:
                await customer_message.send_text(msg.from_user, reply.text)
            elif reply.msg_type == "image" and reply.media_id:
                await customer_message.send_image(msg.from_user, reply.media_id)
            elif reply.msg_type == "msgmenu" and reply.menu:
                await customer_message.send_menu(
                    msg.from_user,
                    head=reply.menu.get("head", ""),
                    items=reply.menu.get("items", []),
                    tail=reply.menu.get("tail", ""),
                )
        except Exception:
            logger.exception(
                "Failed to send reply to %s: %s", msg.from_user, reply
            )
