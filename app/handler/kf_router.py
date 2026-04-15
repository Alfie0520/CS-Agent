"""微信客服消息分发：接收回调通知 → sync_msg 拉取 → Agent 处理 → 回复。"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict

from app.agent.llm_agent import LLMAgent
from app.channel.kf import KfChannelAdapter
from app.config import get_settings
from app.handler.message_handler import handle_message
from app.kf_api.client import kf_post
from app.kf_api.sync import sync_messages
from app.models.message import IncomingMessage, MsgType

logger = logging.getLogger(__name__)

_kf_channel: KfChannelAdapter | None = None
_kf_agent: LLMAgent | None = None

# 消息去重
_seen_kf_msg_ids: OrderedDict[str, float] = OrderedDict()
_DEDUP_TTL = 60
_DEDUP_MAX = 5000


def _is_duplicate(msg_id: str) -> bool:
    if not msg_id:
        return False
    now = time.time()
    while _seen_kf_msg_ids:
        oldest_key, oldest_time = next(iter(_seen_kf_msg_ids.items()))
        if now - oldest_time > _DEDUP_TTL:
            _seen_kf_msg_ids.pop(oldest_key)
        else:
            break
    if msg_id in _seen_kf_msg_ids:
        return True
    _seen_kf_msg_ids[msg_id] = now
    if len(_seen_kf_msg_ids) > _DEDUP_MAX:
        _seen_kf_msg_ids.popitem(last=False)
    return False


def _ensure_initialized() -> tuple[KfChannelAdapter, LLMAgent]:
    global _kf_channel, _kf_agent
    if _kf_channel is None or _kf_agent is None:
        settings = get_settings()
        _kf_channel = KfChannelAdapter(open_kfid=settings.kf_open_kfid)
        _kf_agent = LLMAgent(channel=_kf_channel)
    return _kf_channel, _kf_agent


async def _transition_to_ai(open_kfid: str, external_userid: str) -> None:
    """将会话状态切换到「智能助手接待」(state=1)，仅在 state=0 时需要。"""
    state_resp = await kf_post(
        "/cgi-bin/kf/service_state/get",
        {"open_kfid": open_kfid, "external_userid": external_userid},
    )
    current_state = state_resp.get("service_state", -1)
    if current_state == 0:
        await kf_post(
            "/cgi-bin/kf/service_state/trans",
            {
                "open_kfid": open_kfid,
                "external_userid": external_userid,
                "service_state": 1,
            },
        )
        logger.info("KF session %s transitioned to AI (state=1)", external_userid)


def _parse_kf_message(raw: dict) -> IncomingMessage | None:
    """将 sync_msg 返回的单条消息 JSON 转为 IncomingMessage。

    目前只处理 text 和 enter_session 事件。
    """
    origin = raw.get("origin", 0)
    # origin: 3=客户发送, 4=系统推送, 5=接待人员发送
    # 只处理客户发送的消息 (origin=3) 和事件 (origin=4)
    if origin == 5:
        return None

    msgtype = raw.get("msgtype", "")
    external_userid = raw.get("external_userid", "")

    if msgtype == "text":
        text_content = raw.get("text", {}).get("content", "")
        return IncomingMessage(
            to_user=raw.get("open_kfid", ""),
            from_user=external_userid,
            create_time=raw.get("send_time", 0),
            msg_type=MsgType.TEXT,
            content=text_content,
            msg_id=raw.get("msgid", ""),
            channel="kf",
        )
    elif msgtype == "event":
        event_type = raw.get("event", {}).get("event_type", "")
        if event_type == "enter_session":
            logger.info("KF enter_session: user=%s", external_userid)
        return None

    logger.debug("KF ignoring msgtype=%s from user=%s", msgtype, external_userid)
    return None


async def kf_dispatch(callback_token: str = "") -> None:
    """从 sync_msg 拉取消息并逐条处理。"""
    channel, agent = _ensure_initialized()
    settings = get_settings()

    data = await sync_messages(
        token=callback_token,
        open_kfid=settings.kf_open_kfid,
    )

    if data.get("errcode", 0) != 0:
        logger.error("sync_msg failed: %s", data)
        return

    msg_list = data.get("msg_list", [])
    if not msg_list:
        return

    for raw_msg in msg_list:
        msgid = raw_msg.get("msgid", "")
        if _is_duplicate(msgid):
            continue

        msg = _parse_kf_message(raw_msg)
        if msg is None:
            continue

        # 确保会话在「智能助手」状态
        await _transition_to_ai(settings.kf_open_kfid, msg.from_user)

        logger.info(
            "KF received: type=%s from=%s msgid=%s",
            msg.msg_type.value, msg.from_user, msg.msg_id,
        )
        try:
            await handle_message(msg, agent, channel)
        except Exception:
            logger.exception("KF handle_message failed for %s", msg.from_user)

    # 如果还有更多消息，继续拉取
    if data.get("has_more", 0) == 1:
        await kf_dispatch(callback_token=callback_token)
