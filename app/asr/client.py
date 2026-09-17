"""语音转文字：调用阿里云百炼（DashScope）把音频文件转成文本。

百炼的 Qwen3-ASR-Flash 走 OpenAI 兼容的 /chat/completions：
音频以 Data URI 形式放在 messages[].content[].input_audio.data 中，
识别结果取 choices[0].message.content。

注意：微信下发的是 AMR，而百炼不接受 AMR，需先转成 mp3（见 app/asr/audio.py）。
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_CHAT_PATH = "/chat/completions"
_TIMEOUT = 60

# 百炼要求 Base64 音频带 Data URI 前缀
_MIME_BY_SUFFIX = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".opus": "audio/opus",
    ".ogg": "audio/ogg",
}


def _data_uri(path: Path) -> str:
    mime = _MIME_BY_SUFFIX.get(path.suffix.lower(), "audio/mpeg")
    encoded = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{encoded}"


async def transcribe(audio_path: str | Path) -> str | None:
    """把音频文件转成文本，失败返回 None（调用方负责降级提示）。"""
    settings = get_settings()
    if not settings.asr_api_key:
        logger.error("ASR skipped: ASR_API_KEY not configured")
        return None

    path = Path(audio_path)
    if not path.exists():
        logger.error("ASR skipped: audio file not found: %s", path)
        return None

    payload: dict[str, object] = {
        "model": settings.asr_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": _data_uri(path)},
                    }
                ],
            }
        ],
        "stream": False,
    }
    # 不配置语言时交给模型自动判断
    if settings.asr_language:
        payload["asr_options"] = {"language": settings.asr_language}

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.asr_base_url.rstrip('/')}{_CHAT_PATH}",
                headers={"Authorization": f"Bearer {settings.asr_api_key}"},
                json=payload,
            )
    except Exception:
        logger.exception(
            "ASR request failed elapsed_ms=%.1f",
            (time.perf_counter() - started) * 1000,
        )
        return None

    elapsed_ms = (time.perf_counter() - started) * 1000
    if resp.status_code != 200:
        logger.error(
            "ASR http_error status=%s elapsed_ms=%.1f body=%s",
            resp.status_code,
            elapsed_ms,
            resp.text[:300],
        )
        return None

    try:
        data = resp.json()
        text = (data["choices"][0]["message"]["content"] or "").strip()
    except (ValueError, KeyError, IndexError, TypeError):
        logger.error(
            "ASR unexpected_response elapsed_ms=%.1f body=%s",
            elapsed_ms,
            resp.text[:300],
        )
        return None

    logger.info("ASR ok elapsed_ms=%.1f chars=%s", elapsed_ms, len(text))
    return text or None
