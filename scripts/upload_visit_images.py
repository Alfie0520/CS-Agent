#!/usr/bin/env python3
"""批量上传参访方案图片到微信永久素材库，并写入 media_index.json。

目录结构示例：
    /path/to/images/
    ├── 01广东/
    │   └── 广东-深圳/
    │       ├── 华为松山湖.png
    │       └── 大疆.png
    └── 09河南/
        ├── 胖东来.png
        └── 双汇.png

用法：
    cd /path/to/CS-Agent
    python scripts/upload_visit_images.py /path/to/images

    索引写入 media_index.json，该文件不应提交到代码仓库。
    已存在的 (category, image_name) 会跳过，实现增量上传。
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录加入 path，以便 import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.media_index import exists, get_index_path, upsert
from app.wechat_api.material import add_material_image
from app.wechat_api.token_manager import token_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}


def _collect_images(root: Path) -> list[tuple[str, Path]]:
    """递归收集图片，category = 图片所在文件夹名。跳过 ._ 等系统文件。"""
    items: list[tuple[str, Path]] = []

    def walk(parent: Path) -> None:
        for p in parent.iterdir():
            if p.name.startswith("._") or p.name == "__MACOSX":
                continue
            if p.is_file() and p.suffix.lower() in _SUPPORTED_SUFFIXES:
                items.append((parent.name, p))
            elif p.is_dir():
                walk(p)

    for subdir in sorted(root.iterdir()):
        if subdir.is_dir() and not subdir.name.startswith("._"):
            walk(subdir)

    return items


async def upload_dir(root: Path) -> None:
    """遍历目录，按「分类=图片所在文件夹名」上传图片并写入索引。已存在则跳过。"""
    items = _collect_images(root)
    if not items:
        logger.warning("未找到图片，目录结构应为：根目录/分类名/图片文件")
        return

    logger.info("共发现 %d 张图片，开始上传（已存在将跳过）...", len(items))
    ok, skip, fail = 0, 0, 0

    for category, file_path in items:
        image_name = file_path.name
        if exists(category, image_name):
            skip += 1
            logger.debug("[%s] %s 已存在，跳过", category, image_name)
            continue
        try:
            result = await add_material_image(file_path)
            if "media_id" in result:
                media_id = result["media_id"]
                upsert(media_id, image_name, category)
                ok += 1
                logger.info("[%s] %s -> %s", category, image_name, media_id)
            else:
                fail += 1
                logger.error("[%s] %s 上传失败: %s", category, image_name, result)
        except Exception:
            fail += 1
            logger.exception("[%s] %s 上传异常", category, image_name)

    logger.info("完成：成功 %d，跳过 %d，失败 %d，索引已写入 %s", ok, skip, fail, get_index_path())


def main() -> None:
    parser = argparse.ArgumentParser(description="批量上传参访方案图片到微信永久素材库")
    parser.add_argument("path", type=str, help="图片根目录路径，子文件夹名即为分类（地理位置）")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        logger.error("路径不存在: %s", root)
        sys.exit(1)
    if not root.is_dir():
        logger.error("请指定目录: %s", root)
        sys.exit(1)

    async def run() -> None:
        await token_manager.start()
        try:
            await upload_dir(root)
        finally:
            await token_manager.stop()

    asyncio.run(run())


if __name__ == "__main__":
    main()
