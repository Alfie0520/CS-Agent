"""事件处理：subscribe/unsubscribe/CLICK 等。"""

from __future__ import annotations

import logging

from app.agent.base import BaseAgent
from app.channel.base import ChannelAdapter
from app.models.message import EventType, IncomingMessage

logger = logging.getLogger(__name__)


async def handle_event(
    msg: IncomingMessage, agent: BaseAgent, channel: ChannelAdapter
) -> None:
    if msg.event == EventType.UNSUBSCRIBE:
        logger.info("User %s unsubscribed", msg.from_user)
        return

    response = await agent.handle(msg)

    if not response.replies:
        return

    for reply in response.replies:
        try:
            if reply.msg_type == "text" and reply.text:
                await channel.send_text(msg.from_user, reply.text)
        except Exception:
            logger.exception(
                "Failed to send event reply to %s: %s", msg.from_user, reply
            )
