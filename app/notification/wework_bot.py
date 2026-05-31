"""企业微信群机器人通知。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Awaitable, Callable
from zoneinfo import ZoneInfo

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

PostJson = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


def ensure_keyword(content: str, keyword: str) -> str:
    text = content.strip()
    if keyword and keyword not in text:
        return f"【{keyword}】\n{text}"
    return text


async def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def _is_feishu_webhook(url: str) -> bool:
    return "open.feishu.cn/open-apis/bot/" in url or "open.larksuite.com/open-apis/bot/" in url


def _build_payload(url: str, content: str) -> dict[str, Any]:
    if _is_feishu_webhook(url):
        return {"msg_type": "text", "content": {"text": content}}
    return {"msgtype": "text", "text": {"content": content}}


def _is_success_response(url: str, data: dict[str, Any]) -> bool:
    if _is_feishu_webhook(url):
        return data.get("code", 0) == 0
    return data.get("errcode", 0) == 0


async def send_wework_bot_text(
    content: str,
    *,
    webhook_url: str | None = None,
    keyword: str | None = None,
    post_json: PostJson | None = None,
) -> dict[str, Any]:
    if webhook_url is None or keyword is None:
        settings = get_settings()
        target_url = (webhook_url or settings.feishu_bot_webhook_url or settings.wework_bot_webhook_url).strip()
        bot_keyword = keyword if keyword is not None else settings.wework_bot_keyword
    else:
        target_url = webhook_url.strip()
        bot_keyword = keyword
    if not target_url:
        return {"success": False, "errcode": -1, "errmsg": "WEWORK_BOT_WEBHOOK_URL is not configured"}

    final_content = ensure_keyword(content, bot_keyword)
    payload = _build_payload(target_url, final_content)
    sender = post_json or _post_json
    data = await sender(target_url, payload)
    success = _is_success_response(target_url, data)
    if not success:
        logger.warning("wework bot notify failed: %s", data)
    return {"success": success, **data}


def build_colleague_notification(
    *,
    channel: str,
    user_id: str,
    reason: str,
    summary: str,
    recommended_action: str = "",
    urgency: str = "normal",
    customer_profile: str = "",
    occurred_at: datetime | None = None,
) -> str:
    happened_at = occurred_at or datetime.now(ZoneInfo("Asia/Shanghai"))
    channel_label = {
        "kf": "微信客服",
        "official_account": "公众号",
    }.get(channel, channel or "未知渠道")
    urgency_label = {
        "urgent": "紧急",
        "high": "高",
        "normal": "普通",
        "low": "低",
    }.get((urgency or "normal").lower(), urgency or "普通")

    lines = [
        "CS-Agent 高意向客户提醒",
        "",
        f"发生时间：{happened_at.strftime('%Y-%m-%d %H:%M')}",
        f"跟进优先级：{urgency_label}",
        f"客户来源：{channel_label}",
        f"客户标识：{user_id}",
        "",
        "为什么值得跟进：",
        reason.strip() or "客户出现高意向行为，需要人工判断是否承接。",
        "",
        "案发现场：",
        summary.strip() or "客户表达了进一步咨询意向，请查看会话上下文。",
    ]
    if customer_profile:
        lines.extend(["", "简要用户画像：", customer_profile.strip()])
    if recommended_action:
        lines.extend(["", "建议下一步：", recommended_action.strip()])
    return "\n".join(lines)
