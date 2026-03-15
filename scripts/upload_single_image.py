#!/usr/bin/env python3
"""上传单张图片到微信永久素材库，并输出 media_id。

用法：
    python scripts/upload_single_image.py /path/to/image.jpg

    将输出的 media_id 填入 .env 的 WECHAT_QR_CODE_MEDIA_ID（用于老板微信二维码等）。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.wechat_api.material import add_material_image
from app.wechat_api.token_manager import token_manager


async def main(path: Path) -> None:
    await token_manager.start()
    try:
        result = await add_material_image(path)
        if "media_id" in result:
            print(result["media_id"])
        else:
            print(f"上传失败: {result}", file=sys.stderr)
            sys.exit(1)
    finally:
        await token_manager.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str)
    args = parser.parse_args()
    p = Path(args.path).resolve()
    if not p.exists():
        print(f"文件不存在: {p}", file=sys.stderr)
        sys.exit(1)
    asyncio.run(main(p))
