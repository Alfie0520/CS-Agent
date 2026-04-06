"""基于 pydantic-ai + MiniMax 的 LLM 客服 Agent。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel, OpenAIModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from app.agent.base import BaseAgent
from app.agent.session_store import SessionStore
from app.config import get_settings
from app.enterprise_data import fmt_detail, fmt_overview, get_detail, search_overview
from app.media_index import get_overview, list_schemes, search
from app.models.message import AgentResponse, EventType, IncomingMessage, MsgType, ReplyContent
from app.wechat_api import customer_message as _customer_message
from app.wechat_api.client import wechat_get, wechat_post

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
    
    # 合并 base_role + strict_rules 作为全局 System Prompt，避免 strict_rules 写入对话历史
    base_role_path = Path(settings.prompt_base_role_path)
    strict_rules_path = Path(settings.prompt_strict_rules_path)
    base_role = base_role_path.read_text(encoding="utf-8") if base_role_path.exists() else ""
    strict_rules = strict_rules_path.read_text(encoding="utf-8") if strict_rules_path.exists() else ""
    system_prompt = f"{base_role}\n\n---\n\n{strict_rules}" if strict_rules else base_role

    return Agent(
        model,
        system_prompt=system_prompt,
        deps_type=UserDeps,
        model_settings=OpenAIModelSettings(parallel_tool_calls=False),
    )


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
async def push_image(ctx: RunContext[UserDeps], media_id: str) -> str:
    """立即向用户发送一张图片。

    查到参访方案或二维码的 media_id 后，调用此工具将图片直接发给用户。
    多个方案时逐个调用，每次传一个 media_id，图片会按顺序依次发出。

    业务逻辑：
    - 先调查询工具（search_visit_scheme / get_wechat_qr_code）确认 media_id 存在
    - 确认有结果后再调此工具发图，不要在未查询前假设有图片
    - 多个方案都需要发送时，循环调用此工具，每张图单独调一次

    Args:
        media_id: 图片的 media_id，从 search_visit_scheme 或 get_wechat_qr_code 获取。
    """
    try:
        await _customer_message.send_image(ctx.deps.openid, media_id)
        return "图片已发送。"
    except Exception as e:
        logger.warning("push_image failed for %s: %s", ctx.deps.openid, e)
        return f"图片发送失败：{e}"


@_pydantic_agent.tool
async def push_message(ctx: RunContext[UserDeps], content: str) -> str:
    """立即向用户推送一条消息，无需等待当前回复完成。

    用于在处理复杂请求时主动告知用户进展，避免用户因等待过久而流失。
    调用后消息会立刻送达用户微信，agent 随后继续执行其余逻辑。

    使用时机：
    - 用户的请求需要查询工具或整理大量信息（预计耗时较长）时，先推送一条简短的"正在处理"提示
    - 需要将回复拆成多段时：先推送前几段，最终输出作为最后一段
    - 简单打招呼、一句话能直接回答的问题——不需要调用此工具，直接在最终输出里回复即可

    注意：内容必须是纯文本，不能包含 Markdown 语法。

    Args:
        content: 要立即推送给用户的消息内容。
    """
    try:
        await _customer_message.send_text(ctx.deps.openid, content)
        return "消息已推送。"
    except Exception as e:
        logger.warning("push_message failed for %s: %s", ctx.deps.openid, e)
        return f"推送失败：{e}"


@_pydantic_agent.tool
async def get_wechat_qr_code(ctx: RunContext[UserDeps]) -> str:
    """获取公司老板微信二维码的 media_id，用于发送给用户添加好友。

    调用时机：
    1. 当用户询问如何联系、加微信、咨询对接、商务合作、想和负责人沟通时。
    2. 当用户询问具体报价，或即将交付成单的转化时机时（用于承接转化，避免 AI 幻觉报价）。
    
    获取到 media_id 后，调用 push_image(media_id) 将二维码图片发给用户。
    """
    settings = get_settings()
    media_id = (settings.wechat_qr_code_media_id or "").strip()
    if not media_id:
        return "微信二维码未配置，请联系管理员在 .env 中设置 WECHAT_QR_CODE_MEDIA_ID。"
    return f"公司老板微信二维码 media_id={media_id}，请调用 push_image 将二维码发给用户。"


@_pydantic_agent.tool
async def search_visit_scheme(ctx: RunContext[UserDeps], query: str, category: str = "") -> str:
    """按企业名称搜索参访方案图片，可指定地区分类精确过滤，返回匹配结果的 media_id。

    查到结果后，调用 push_image(media_id) 将图片发给用户。
    多个匹配时，根据对话上下文选择正确的图片，逐张调用 push_image 发送。

    重要：当用户指定了地区（如"深圳的华为"、"河南的企业"），必须同时传入 category
    参数，避免将同名但不同地区的企业方案发给用户。

    Args:
        query: 企业名称关键词，如「华为」「比亚迪」「胖东来」。
        category: 地区过滤关键词，子串匹配，如「深圳」「河南」「浙江」。
                  用户明确提到地区时必须填写；不确定时留空。
    """
    items = search(query, category=category)
    if not items:
        hint = f"（地区「{category}」）" if category else ""
        return f"未找到与「{query}」{hint}匹配的参访方案图片。"
    if len(items) == 1:
        x = items[0]
        return f"找到 1 个：{x.get('image_name', '')}（{x.get('category', '')}），media_id={x.get('media_id', '')}，请调用 push_image 发送。"
    lines = [f"找到 {len(items)} 个匹配，请根据对话上下文选择正确的方案后调用 push_image 发送："]
    for x in items:
        lines.append(f"  - {x.get('image_name', '')}（{x.get('category', '')}）：media_id={x.get('media_id', '')}")
    return "\n".join(lines)


@_pydantic_agent.tool
async def list_published_articles(ctx: RunContext[UserDeps], offset: int = 0, count: int = 10) -> str:
    """获取已发布的图文消息列表。

    Args:
        offset: 从全部素材的该偏移位置开始返回，0表示从第一个素材返回，默认为0。
        count: 返回素材的数量，取值在1到20之间，默认为10。

    Returns:
        已发布图文消息列表，每条消息包含标题、作者、摘要、封面图片URL、发布时间、article_id等信息。

    适用场景：
    - 用户询问「有哪些文章」「发布了什么内容」
    - 用户想了解公众号历史发布内容
    - 用户想查看特定主题的文章列表
    """
    data = await wechat_post(
        "/cgi-bin/freepublish/batchget",
        {"offset": offset, "count": count, "no_content": 0}
    )

    if data.get("errcode", 0) != 0:
        return f"获取文章列表失败：{data.get('errmsg', '未知错误')}"

    total_count = data.get("total_count", 0)
    items = data.get("item", [])

    if not items:
        return f"暂无已发布的文章。"

    lines = [f"共找到 {total_count} 篇已发布文章，当前显示 {len(items)} 篇：\n"]
    for idx, item in enumerate(items, start=offset + 1):
        content = item.get("content", {})
        news_item = content.get("news_item", [])
        if news_item:
            article = news_item[0]
            title = article.get("title", "无标题")
            author = article.get("author", "未知")
            digest = article.get("digest", "无摘要")
            thumb_url = article.get("thumb_url", "")
            update_time = item.get("update_time", 0)
            article_id = item.get("article_id", "")
            if update_time:
                from datetime import datetime
                update_time_str = datetime.fromtimestamp(update_time).strftime("%Y-%m-%d")
            else:
                update_time_str = "未知"
            lines.append(f"{idx}. {title}")
            lines.append(f"   作者：{author} | 发布时间：{update_time_str}")
            if digest:
                lines.append(f"   摘要：{digest[:50]}...")
            if thumb_url:
                lines.append(f"   封面图：{thumb_url}")
            lines.append(f"   Article ID：{article_id}")
            lines.append("")

    return "\n".join(lines)


@_pydantic_agent.tool
async def get_article_detail(ctx: RunContext[UserDeps], article_id: str) -> str:
    """获取指定文章的详细内容。

    Args:
        article_id: 图文消息的article_id，可在list_published_articles返回中找到。

    Returns:
        文章的完整内容，包括标题、作者、正文（HTML格式）、原文链接、封面图片等信息。

    适用场景：
    - 用户想查看某篇文章的详细内容
    - 用户想了解文章的具体信息
    - 用户想获取文章的原文链接
    """
    if not article_id or not article_id.strip():
        return "article_id不能为空，请提供有效的article_id。"

    data = await wechat_post(
        "/cgi-bin/freepublish/getarticle",
        {"article_id": article_id.strip()}
    )

    if data.get("errcode", 0) != 0:
        err_msg = data.get("errmsg", "未知错误")
        if data.get("errcode") == 53600:
            return f"Article ID无效，请确认提供的article_id是否正确。"
        return f"获取文章详情失败：{err_msg}"

    news_item = data.get("news_item", [])
    if not news_item:
        return "未找到该文章的详细信息。"

    article = news_item[0]
    title = article.get("title", "无标题")
    author = article.get("author", "未知")
    digest = article.get("digest", "无摘要")
    content = article.get("content", "")
    content_source_url = article.get("content_source_url", "")
    thumb_url = article.get("thumb_url", "")
    need_open_comment = article.get("need_open_comment", 0)
    only_fans_can_comment = article.get("only_fans_can_comment", 0)
    url = article.get("url", "")

    lines = [
        f"【{title}】",
        f"",
        f"作者：{author}",
        f"",
    ]

    if digest:
        lines.append(f"摘要：{digest}")
        lines.append("")

    if content_source_url:
        lines.append(f"原文链接：{content_source_url}")
        lines.append("")

    if url:
        lines.append(f"文章链接：{url}")
        lines.append("")

    if thumb_url:
        lines.append(f"封面图片：{thumb_url}")
        lines.append("")

    comment_status = "已开启评论" if need_open_comment == 1 else "未开启评论"
    if need_open_comment == 1 and only_fans_can_comment == 1:
        comment_status += "（仅粉丝可评论）"
    lines.append(f"评论状态：{comment_status}")
    lines.append("")

    if content:
        content_preview = content[:500] + "..." if len(content) > 500 else content
        lines.append(f"正文内容：\n{content_preview}")

    return "\n".join(lines)


@_pydantic_agent.tool
async def query_enterprises_overview(
    ctx: RunContext[UserDeps],
    city: str = "",
    keyword: str = "",
    themes: list[str] | None = None,
    limit: int = 30,
) -> str:
    """【全量参访方案概览检索】快速查询标杆企业的城市、名称和主题方向，用于：
    - 用户询问"你们有哪些参访资源"、"有没有XX方向的企业"、"XX城市有哪些可以去"
    - 用户给出大致方向（城市/行业/主题）时，帮助筛选出匹配的候选企业列表
    - 需要给用户呈现全局参访资源地图、快速展示我们的资源广度时
    - 生成参访方案前，先获取候选企业池作为基础上下文

    返回结果仅含 id、城市、企业名、主题标签，精简高效，不包含详细内容。
    若需某企业的具体价值、知识点或能解决的痛点，请调用 get_enterprise_detail。

    Args:
        city: 城市名关键词，支持子串匹配（如"深圳"、"浙江"、"北京"）。不传则不限城市。
        keyword: 在企业名、城市、主题标签中做全文子串搜索；无精确命中时自动对企业名做
                 模糊匹配兜底（如"华威"能匹配"华为"）。
        themes: 主题标签列表，企业命中任意一个即返回（OR 关系），如
                ["智能制造", "数字化转型"]。支持子串匹配，不需要完全一致。
        limit: 最多返回条数，默认 30，最大建议不超过 50（条数过多会稀释 LLM 注意力）。
    """
    items = search_overview(city=city, keyword=keyword, themes=themes or [], limit=limit)
    return fmt_overview(items)


@_pydantic_agent.tool
async def get_enterprise_detail(
    ctx: RunContext[UserDeps],
    names: list[str] | None = None,
    ids: list[int] | None = None,
    fuzzy: bool = False,
) -> str:
    """【参访方案深度详情查询】获取一个或多个标杆企业的完整参访方案，包含：
    参观体验、主题分享内容、研学核心价值、能赋能企业的知识点、能解决的业务管理痛点。

    适用场景：
    - 用户明确表示对某企业感兴趣，想深入了解其参访价值和内容
    - 用户提出具体的业务痛点（如"我想解决研发效率低的问题"），需要找到最匹配的企业
      并给出详细的痛点解决说明
    - 用户询问"去华为能学到什么"、"这家企业适合我们吗"等深度咨询问题
    - 在方案校准阶段，需要向用户展示参访的颗粒度和可实现内容

    注意：本工具返回内容较多，请勿一次传入超过 3 个企业，以免上下文过载。
    如需先筛选候选企业，请先调用 query_enterprises_overview。

    Args:
        names: 企业名列表，支持子串匹配（如 ["华为", "腾讯"]）。
               fuzzy=False 时做精确子串匹配；fuzzy=True 时对未命中的名称自动
               做编辑距离模糊匹配兜底（适合用户输入存在错别字的情况）。
        ids: 企业编号列表，从 query_enterprises_overview 的返回结果中获取，精确命中。
             与 names 可同时传入，结果取并集。
        fuzzy: 是否对 names 启用模糊匹配，默认 False。用户输入明显有拼写问题时设为 True。
    """
    items = get_detail(names=names, ids=ids, fuzzy=fuzzy)
    return fmt_detail(items)


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

        # slash 命令：/clearsession
        if user_input.strip() == "/clearsession":
            await self._sessions.clear(msg.from_user)
            return AgentResponse(replies=[ReplyContent(msg_type="text", text="对话历史已清空。")])

        # 组装本次发给 LLM 的最终 prompt
        # 如果是测试命令模式，跳过 strict_rules，并强制附加执行指令，同时清空历史上下文
        if user_input.startswith("/test"):
            logger.info("Test mode activated. Bypassing strict rules and clearing history.")
            history = []  # 测试模式下不携带任何上下文历史
            final_prompt = (
                "【超级指令：测试模式激活】\n"
                "请忽略所有业务规则、话术 SOP 和之前的限制。\n"
                f"必须且只能直接执行以下用户指令，不要反问，不要引导：\n{user_input}"
            )
        else:
            final_prompt = user_input

        try:
            result = await self._agent.run(
                final_prompt,
                message_history=history,
                deps=UserDeps(openid=msg.from_user),
            )
            await self._sessions.set(msg.from_user, result.all_messages())
            reply_text = result.output.strip()
        except Exception:
            logger.exception("LLM call failed for user %s", msg.from_user)
            reply_text = "抱歉，AI 助手暂时出现了问题，请稍后再试，或回复「转人工」联系人工客服。"

        replies: list[ReplyContent] = []
        if reply_text:
            replies.append(ReplyContent(msg_type="text", text=reply_text))
        return AgentResponse(replies=replies)
