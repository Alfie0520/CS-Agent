from __future__ import annotations

from app.agent.base import BaseAgent
from app.models.message import (
    AgentResponse,
    EventType,
    IncomingMessage,
    MsgType,
    ReplyContent,
)

_WELCOME = (
    "你好，欢迎关注！\n"
    "我是 AI 客服助手，有任何问题请直接发送文字消息，我会尽力为您解答。"
)

_DEFAULT_TEXT_REPLY = (
    "您好，我是 AI 客服助手。\n"
    "目前正在升级中，暂时只能提供基础问答服务。\n"
    "如需人工客服，请回复「转人工」。"
)

_UNSUPPORTED_TYPE_REPLY = "暂不支持该类型消息，请发送文字进行咨询。"

_MENU_REPLIES: dict[str, str] = {
    "mpGuide": "开发指引功能正在建设中，敬请期待。",
}


class DefaultAgent(BaseAgent):
    """Hardcoded 默认回复 Agent，用于基础自动回复。"""

    async def handle(self, message: IncomingMessage) -> AgentResponse:
        if message.msg_type == MsgType.EVENT:
            return self._handle_event(message)
        return self._handle_message(message)

    def _handle_event(self, msg: IncomingMessage) -> AgentResponse:
        if msg.event == EventType.SUBSCRIBE:
            return AgentResponse(
                replies=[ReplyContent(msg_type="text", text=_WELCOME)]
            )

        if msg.event == EventType.CLICK:
            text = _MENU_REPLIES.get(msg.event_key or "", _DEFAULT_TEXT_REPLY)
            return AgentResponse(
                replies=[ReplyContent(msg_type="text", text=text)]
            )

        # unsubscribe / SCAN / LOCATION / VIEW 等不需要回复
        return AgentResponse()

    def _handle_message(self, msg: IncomingMessage) -> AgentResponse:
        if msg.msg_type == MsgType.TEXT:
            content = (msg.content or "").strip()

            if content == "转人工":
                return AgentResponse(
                    replies=[
                        ReplyContent(msg_type="transfer_customer_service")
                    ],
                    use_passive_reply=True,
                )

            return AgentResponse(
                replies=[ReplyContent(msg_type="text", text=_DEFAULT_TEXT_REPLY)]
            )

        # 图片/语音/视频/位置/链接 → 统一提示
        return AgentResponse(
            replies=[ReplyContent(msg_type="text", text=_UNSUPPORTED_TYPE_REPLY)]
        )
