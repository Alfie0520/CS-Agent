"""基于 pydantic-ai + MiniMax 的 LLM 客服 Agent。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agent.base import BaseAgent
from app.agent.session_store import SessionStore
from app.config import get_settings
from app.media_index import get_overview, list_schemes, search
from app.models.message import AgentResponse, EventType, IncomingMessage, MsgType, ReplyContent
from app.wechat_api.client import wechat_get

logger = logging.getLogger(__name__)

_SUBSCRIBE_SCENE: dict[str, str] = {
    "ADD_SCENE_SEARCH": "搜索公众号",
    "ADD_SCENE_QR_CODE": "扫描二维码",
    "ADD_SCENE_PROFILE_CARD": "名片分享",
    "ADD_SCENE_PROFILE_LINK": "图文页内名称点击",
    "ADD_SCENE_WECHAT_ADVERTISEMENT": "微信广告",
    "ADD_SCENE_WXA": "小程序关注",
    "ADD_SCENE_OTHERS": "其他",
}


@dataclass
class UserDeps:
    """每次请求注入的用户上下文，供工具函数使用。"""
    openid: str


def _build_pydantic_agent() -> Agent[UserDeps, str]:
    settings = get_settings()
    model = OpenAIModel(
        settings.minimax_model,
        provider=OpenAIProvider(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
        ),
    )
    return Agent(model, system_prompt=settings.minimax_system_prompt, deps_type=UserDeps)


# 模块级 Agent 实例，工具通过装饰器注册在此
_pydantic_agent: Agent[UserDeps, str] = _build_pydantic_agent()


@_pydantic_agent.tool
async def get_user_info(ctx: RunContext[UserDeps]) -> str:
    """查询当前用户的微信公众号关注信息。

    返回内容包括：关注状态、关注时间、关注来源渠道、运营者设置的备注名、标签 ID 列表。

    注意：由于微信平台限制（2021 年 12 月起），该接口不再返回用户昵称和头像。

    适用场景：
    - 用户询问自己的账号或关注状态时
    - 需要了解用户是何时、通过何种渠道关注的
    - 根据运营者备注名或标签提供个性化服务时
    不适用场景：获取用户姓名、头像等个人信息（平台已不支持）。
    """
    data = await wechat_get(
        "/cgi-bin/user/info",
        {"openid": ctx.deps.openid, "lang": "zh_CN"},
    )

    if data.get("subscribe", 0) == 0:
        return "该用户尚未关注公众号，无法获取关注信息。"

    subscribe_ts = data.get("subscribe_time", 0)
    subscribe_time_str = (
        datetime.fromtimestamp(subscribe_ts).strftime("%Y-%m-%d")
        if subscribe_ts else "未知"
    )
    scene = _SUBSCRIBE_SCENE.get(
        data.get("subscribe_scene", ""), data.get("subscribe_scene", "未知")
    )
    remark = data.get("remark") or "无"
    tags = data.get("tagid_list", [])

    return (
        f"关注状态：已关注\n"
        f"关注时间：{subscribe_time_str}\n"
        f"关注来源：{scene}\n"
        f"备注名：{remark}\n"
        f"标签 ID 列表：{tags if tags else '无'}"
    )


@_pydantic_agent.tool
async def get_visit_scheme_overview(ctx: RunContext[UserDeps]) -> str:
    """查看参访方案概览：有多少个地理位置分类、每个分类下有多少个方案。

    分类名即文件夹名，按地理位置命名（如 09河南、广东-深圳）。
    用于回答「有哪些参访方案」「覆盖哪些地区」「一共多少方案」等。
    """
    data = get_overview()
    total = data.get("total", 0)
    cats = data.get("categories", {})
    lines = [f"参访方案总数：{total} 个", "按地理位置分类："]
    for name, count in cats.items():
        lines.append(f"  - {name}：{count} 个")
    return "\n".join(lines)


@_pydantic_agent.tool
async def list_visit_schemes(ctx: RunContext[UserDeps], category: str = "") -> str:
    """按地理位置（分类）列出该地区下的所有企业参访方案。

    Args:
        category: 分类名（如 09河南、广东-深圳），为空则列出全部方案。
    """
    items = list_schemes(category=category if category else None)
    if not items:
        return f"未找到方案。" + (f"（分类「{category}」不存在或为空）" if category else "")
    lines = [f"共 {len(items)} 个方案："]
    for x in items:
        lines.append(f"  - {x.get('image_name', '')}（{x.get('category', '')}）")
    return "\n".join(lines)


@_pydantic_agent.tool
async def search_visit_scheme(ctx: RunContext[UserDeps], query: str) -> str:
    """按地理位置或企业名称搜索参访方案，返回匹配的 media_id 供发送图片。

    Args:
        query: 搜索关键词，如「华为」「深圳」「河南」等。

    Returns:
        匹配结果，包含 media_id。若需发送图片，在回复末尾写 IMAGE:media_id。
    """
    items = search(query)
    if not items:
        return f"未找到与「{query}」匹配的参访方案。"
    if len(items) == 1:
        x = items[0]
        return f"找到：{x.get('image_name', '')}（{x.get('category', '')}），media_id={x.get('media_id', '')}。回复时在末尾写 IMAGE:{x.get('media_id', '')} 即可发送。"
    lines = [f"找到 {len(items)} 个匹配，请选一个发送："]
    for x in items:
        lines.append(f"  - {x.get('image_name', '')}（{x.get('category', '')}）：IMAGE:{x.get('media_id', '')}")
    return "\n".join(lines)


_WELCOME = (
    "你好，欢迎关注！\n"
    "我是 AI 客服助手，有任何问题请直接发送文字消息，我会尽力为您解答。\n"
    "如需人工客服，请回复「转人工」。"
)

_UNSUPPORTED_TYPE_REPLY = "暂不支持该类型消息，请发送文字进行咨询。"


class LLMAgent(BaseAgent):
    """pydantic-ai + MiniMax 驱动的客服 Agent，支持多轮对话与工具调用。"""

    def __init__(self) -> None:
        settings = get_settings()
        self._agent = _pydantic_agent
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
            result = await self._agent.run(
                user_input,
                message_history=history,
                deps=UserDeps(openid=msg.from_user),
            )
            await self._sessions.set(msg.from_user, result.all_messages())
            reply_text = result.output.strip()
        except Exception:
            logger.exception("LLM call failed for user %s", msg.from_user)
            reply_text = "抱歉，AI 助手暂时出现了问题，请稍后再试，或回复「转人工」联系人工客服。"

        # 解析 IMAGE:media_id，取最后一个（LLM 选定要发送的）
        replies: list[ReplyContent] = []
        image_media_id: str | None = None
        matches = re.findall(r"IMAGE:(\S+)", reply_text)
        if matches:
            image_media_id = matches[-1].strip()
            reply_text = re.sub(r"IMAGE:\S+", "", reply_text)  # 移除所有 IMAGE:xxx
            reply_text = re.sub(r"\n{2,}", "\n", reply_text).strip()  # 合并多余空行

        if reply_text:
            replies.append(ReplyContent(msg_type="text", text=reply_text))
        if image_media_id:
            replies.append(ReplyContent(msg_type="image", media_id=image_media_id))

        return AgentResponse(replies=replies)
