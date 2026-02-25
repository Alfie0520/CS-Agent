"""消息分发入口：解析 XML → 排重 → 路由到 handler → 发送回复。"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict

from app.agent.default_agent import DefaultAgent
from app.core.xml_parser import build_transfer_kf_xml, parse_xml
from app.handler.event_handler import handle_event
from app.handler.message_handler import handle_message
from app.models.message import MsgType

logger = logging.getLogger(__name__)

_agent = DefaultAgent()

_seen_msg_ids: OrderedDict[str, float] = OrderedDict()
_DEDUP_TTL = 30  # 30 秒内同一 MsgId 视为重复
_DEDUP_MAX = 5000


def _is_duplicate(msg_id: str | None) -> bool:
    """MsgId 幂等检查，防止微信 3 次重试导致重复处理。"""
    if not msg_id:
        return False

    now = time.time()
    # 清理过期条目
    while _seen_msg_ids:
        oldest_key, oldest_time = next(iter(_seen_msg_ids.items()))
        if now - oldest_time > _DEDUP_TTL:
            _seen_msg_ids.pop(oldest_key)
        else:
            break

    if msg_id in _seen_msg_ids:
        return True

    _seen_msg_ids[msg_id] = now
    if len(_seen_msg_ids) > _DEDUP_MAX:
        _seen_msg_ids.popitem(last=False)
    return False


async def dispatch(raw_xml: bytes) -> None:
    """Background task 入口：解析消息并分发处理。"""
    try:
        msg = parse_xml(raw_xml)
    except Exception:
        logger.exception("Failed to parse XML: %s", raw_xml[:500])
        return

    if _is_duplicate(msg.msg_id):
        logger.debug("Duplicate message %s, skipping", msg.msg_id)
        return

    logger.info(
        "Received: type=%s from=%s msg_id=%s",
        msg.msg_type.value,
        msg.from_user,
        msg.msg_id,
    )

    if msg.msg_type == MsgType.EVENT:
        await handle_event(msg, _agent)
    else:
        await handle_message(msg, _agent)
