#!/usr/bin/env python3
"""从旧 /data/media_index.json 恢复公众号永久素材图片到本地资产库。"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.assets.restore import restore_assets_from_media_index
from app.config import get_settings
from app.wechat_api.material import get_material_image


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--media-index", default="/data/media_index.json")
    parser.add_argument("--asset-root", default=settings.asset_root_path)
    parser.add_argument("--asset-index", default=settings.asset_index_path)
    parser.add_argument("--threshold-bytes", type=int, default=1024 * 1024)
    parser.add_argument("--target-bytes", type=int, default=200 * 1024)
    args = parser.parse_args()

    result = restore_assets_from_media_index(
        media_index_path=Path(args.media_index),
        asset_root=Path(args.asset_root),
        asset_index_path=Path(args.asset_index),
        download_material=get_material_image,
        threshold_bytes=args.threshold_bytes,
        target_bytes=args.target_bytes,
    )
    print(result)


if __name__ == "__main__":
    main()
