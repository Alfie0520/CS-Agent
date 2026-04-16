"""微信客服消息发送：POST /cgi-bin/kf/send_msg"""

from __future__ import annotations

import logging
from typing import Any

from app.kf_api.client import kf_post

logger = logging.getLogger(__name__)

_SEND_PATH = "/cgi-bin/kf/send_msg"


async def _send(payload: dict[str, Any]) -> dict[str, Any]:
    return await kf_post(_SEND_PATH, payload)


async def send_text(
    external_userid: str, open_kfid: str, content: str
) -> dict[str, Any]:
    return await _send({
        "touser": external_userid,
        "open_kfid": open_kfid,
        "msgtype": "text",
        "text": {"content": content},
    })


async def send_image(
    external_userid: str, open_kfid: str, media_id: str
) -> dict[str, Any]:
    return await _send({
        "touser": external_userid,
        "open_kfid": open_kfid,
        "msgtype": "image",
        "image": {"media_id": media_id},
    })
