"""语音格式转换。

微信下发的语音是 AMR（客服渠道也可能拿到 Silk），主流 ASR 服务都不直接支持，
统一先转成 16kHz 单声道 mp3 再送识别。
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CONVERT_TIMEOUT = 30


async def to_mp3_16k_mono(src: str | Path, dst: str | Path) -> bool:
    """用 ffmpeg 转为 16kHz 单声道 mp3，失败返回 False。"""
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", str(src),
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "32k",
        str(dst),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=_CONVERT_TIMEOUT)
    except FileNotFoundError:
        logger.error("ffmpeg not found, voice recognition unavailable")
        return False
    except asyncio.TimeoutError:
        logger.error("ffmpeg conversion timed out: %s", src)
        return False

    if proc.returncode != 0:
        logger.error(
            "ffmpeg conversion failed rc=%s detail=%s",
            proc.returncode,
            (stderr or b"").decode(errors="ignore")[:500],
        )
        return False
    return Path(dst).exists()
