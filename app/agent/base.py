from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.message import AgentResponse, IncomingMessage


class BaseAgent(ABC):
    """Agent 抽象基类。本期实现 DefaultAgent，后续替换为 LLMAgent。"""

    @abstractmethod
    async def handle(self, message: IncomingMessage) -> AgentResponse:
        """处理一条微信消息/事件，返回 AgentResponse（含一或多条回复）。"""
