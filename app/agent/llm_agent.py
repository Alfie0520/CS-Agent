"""基于 pydantic-ai + MiniMax 的 LLM 客服 Agent。"""

from __future__ import annotations

import logging

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agent.base import BaseAgent
from app.agent.session_store import SessionStore
from app.config import get_settings
from app.models.message import AgentResponse, EventType, IncomingMessage, MsgType, ReplyContent

logger = logging.getLogger(__name__)


def _build_pydantic_agent() -> Agent[None, str]:
    settings = get_settings()
    model = OpenAIModel(
        settings.minimax_model,
        provider=OpenAIProvider(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
        ),
    )
    return Agent(model, system_prompt=settings.minimax_system_prompt)


_WELCOME = (
    "你好，欢迎关注！\n"
    "我是 AI 客服助手，有任何问题请直接发送文字消息，我会尽力为您解答。\n"
    "如需人工客服，请回复「转人工」。"
)

_UNSUPPORTED_TYPE_REPLY = "暂不支持该类型消息，请发送文字进行咨询。"


class LLMAgent(BaseAgent):
    """pydantic-ai + MiniMax 驱动的客服 Agent，支持多轮对话。"""

    def __init__(self) -> None:
        settings = get_settings()
        self._agent = _build_pydantic_agent()
        self._sessions = SessionStore(db_path=settings.session_db_path, ttl=settings.session_ttl)

    async def handle(self, message: IncomingMessage) -> AgentResponse:
        if message.msg_type == MsgType.EVENT:
            return self._handle_event(message)
        return await self._handle_message(message)

    def _handle_event(self, msg: IncomingMessage) -> AgentResponse:
        if msg.event == EventType.SUBSCRIBE:
            return AgentResponse(replies=[ReplyContent(msg_type="text", text=_WELCOME)])
        # 其他事件（unsubscribe / SCAN / VIEW 等）无需回复
        return AgentResponse()

    async def _handle_message(self, msg: IncomingMessage) -> AgentResponse:
        if msg.msg_type != MsgType.TEXT:
            return AgentResponse(
                replies=[ReplyContent(msg_type="text", text=_UNSUPPORTED_TYPE_REPLY)]
            )

        user_input = (msg.content or "").strip()
        if not user_input:
            return AgentResponse()

        history = await self._sessions.get(msg.from_user)

        try:
            result = await self._agent.run(user_input, message_history=history)
            await self._sessions.set(msg.from_user, result.all_messages())
            reply_text = result.output.strip()
        except Exception:
            logger.exception("LLM call failed for user %s", msg.from_user)
            reply_text = "抱歉，AI 助手暂时出现了问题，请稍后再试，或回复「转人工」联系人工客服。"

        return AgentResponse(replies=[ReplyContent(msg_type="text", text=reply_text)])
