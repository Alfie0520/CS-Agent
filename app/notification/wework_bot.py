"""企业微信群机器人通知。"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

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
) -> str:
    lines = [
        "CS-Agent 线索通知",
        "",
        f"紧急程度：{urgency or 'normal'}",
        f"触发原因：{reason}",
        f"用户渠道：{channel}",
        f"用户 ID：{user_id}",
        "",
        f"对话摘要：{summary}",
    ]
    if recommended_action:
        lines.extend(["", f"建议动作：{recommended_action}"])
    return "\n".join(lines)
