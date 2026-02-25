from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MsgType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"
    SHORT_VIDEO = "shortvideo"
    LOCATION = "location"
    LINK = "link"
    EVENT = "event"


class EventType(str, Enum):
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SCAN = "SCAN"
    LOCATION = "LOCATION"
    CLICK = "CLICK"
    VIEW = "VIEW"


@dataclass
class IncomingMessage:
    """微信推送的原始消息/事件的统一数据模型。"""

    to_user: str
    from_user: str
    create_time: int
    msg_type: MsgType

    # 普通消息公共字段
    msg_id: Optional[str] = None

    # text
    content: Optional[str] = None

    # image
    pic_url: Optional[str] = None
    media_id: Optional[str] = None

    # voice
    format: Optional[str] = None
    media_id_16k: Optional[str] = None

    # video / shortvideo
    thumb_media_id: Optional[str] = None

    # location
    location_x: Optional[float] = None
    location_y: Optional[float] = None
    scale: Optional[int] = None
    label: Optional[str] = None

    # link
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None

    # event 字段
    event: Optional[EventType] = None
    event_key: Optional[str] = None
    ticket: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    precision: Optional[float] = None


@dataclass
class ReplyContent:
    """Agent 产出的单条回复内容。"""

    msg_type: str  # text / image / msgmenu / transfer_customer_service
    text: Optional[str] = None
    media_id: Optional[str] = None
    menu: Optional[dict] = None


@dataclass
class AgentResponse:
    """Agent 处理结果：一个或多条回复。"""

    replies: list[ReplyContent] = field(default_factory=list)
    use_passive_reply: bool = False  # True 时走被动回复 XML（仅用于转人工客服）
