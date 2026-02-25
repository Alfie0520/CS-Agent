from __future__ import annotations

import time
from typing import Optional

from lxml import etree

from app.models.message import EventType, IncomingMessage, MsgType


def _text(root: etree._Element, tag: str) -> Optional[str]:
    el = root.find(tag)
    return el.text if el is not None else None


def _int(root: etree._Element, tag: str) -> Optional[int]:
    v = _text(root, tag)
    return int(v) if v is not None else None


def _float(root: etree._Element, tag: str) -> Optional[float]:
    v = _text(root, tag)
    return float(v) if v is not None else None


def parse_xml(raw: bytes) -> IncomingMessage:
    """将微信推送的 XML 字节解析为 IncomingMessage。"""
    root = etree.fromstring(raw)
    msg_type_str = _text(root, "MsgType")
    msg_type = MsgType(msg_type_str)

    msg = IncomingMessage(
        to_user=_text(root, "ToUserName") or "",
        from_user=_text(root, "FromUserName") or "",
        create_time=_int(root, "CreateTime") or 0,
        msg_type=msg_type,
        msg_id=_text(root, "MsgId"),
    )

    if msg_type == MsgType.TEXT:
        msg.content = _text(root, "Content")

    elif msg_type == MsgType.IMAGE:
        msg.pic_url = _text(root, "PicUrl")
        msg.media_id = _text(root, "MediaId")

    elif msg_type == MsgType.VOICE:
        msg.media_id = _text(root, "MediaId")
        msg.format = _text(root, "Format")
        msg.media_id_16k = _text(root, "MediaId16K")

    elif msg_type in (MsgType.VIDEO, MsgType.SHORT_VIDEO):
        msg.media_id = _text(root, "MediaId")
        msg.thumb_media_id = _text(root, "ThumbMediaId")

    elif msg_type == MsgType.LOCATION:
        msg.location_x = _float(root, "Location_X")
        msg.location_y = _float(root, "Location_Y")
        msg.scale = _int(root, "Scale")
        msg.label = _text(root, "Label")

    elif msg_type == MsgType.LINK:
        msg.title = _text(root, "Title")
        msg.description = _text(root, "Description")
        msg.url = _text(root, "Url")

    elif msg_type == MsgType.EVENT:
        event_str = _text(root, "Event")
        if event_str:
            try:
                msg.event = EventType(event_str)
            except ValueError:
                msg.event = None
        msg.event_key = _text(root, "EventKey")
        msg.ticket = _text(root, "Ticket")
        msg.latitude = _float(root, "Latitude")
        msg.longitude = _float(root, "Longitude")
        msg.precision = _float(root, "Precision")

    return msg


def build_text_reply_xml(to_user: str, from_user: str, content: str) -> str:
    """构建被动回复文本消息 XML。"""
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        "</xml>"
    )


def build_transfer_kf_xml(
    to_user: str, from_user: str, kf_account: Optional[str] = None
) -> str:
    """构建转人工客服的被动回复 XML。"""
    trans_info = ""
    if kf_account:
        trans_info = (
            f"<TransInfo><KfAccount><![CDATA[{kf_account}]]></KfAccount></TransInfo>"
        )
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[transfer_customer_service]]></MsgType>"
        f"{trans_info}"
        "</xml>"
    )
