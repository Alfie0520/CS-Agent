#!/usr/bin/env python3
"""批量处理参访方案图片的增删改操作（通过远程服务器 API）。

工作流程：
1. 准备好图片文件到 data/images/ 目录
2. 在 data/ 目录下创建 ops.json 配置文件
3. 运行脚本自动执行所有操作

data/ops.json 示例：
{
  "operations": [
    {
      "operation": "create",
      "image_path": "images/01广东/广东-深圳/华为松山湖.png",
      "image_name": "华为松山湖.png",
      "category": "01广东"
    },
    {
      "operation": "update",
      "image_path": "images/09河南/胖东来更新.png",
      "image_name": "胖东来.png",
      "category": "09河南",
      "media_id": "原有的media_id"
    },
    {
      "operation": "delete",
      "media_id": "要删除的media_id"
    }
  ]
}

用法：
    cd /path/to/CS-Agent
    python scripts/image_ops/batch_image_operations.py

    或指定配置文件路径：
    python scripts/image_ops/batch_image_operations.py --config /path/to/ops.json
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import logging
import sys
from pathlib import Path

import httpx
from PIL import Image

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
MAX_IMAGE_SIZE = 200 * 1024
REMOTE_API_KEY = "cRgCWNHkfrZt7GE47JQtyE9RDY2Pxo4lAs9DQjuSXUY="

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
OPS_FILE = SCRIPT_DIR / "data" / "ops.json"
REMOTE_API_URL = "https://43.129.183.181/api/visit-image"


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        logger.error("配置文件不存在: %s", config_path)
        sys.exit(1)
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error("配置文件 JSON 格式错误: %s", e)
        sys.exit(1)


def compress_image_to_base64(image_path: Path) -> tuple[str, int] | None:
    try:
        img = Image.open(image_path)
        original_size = image_path.stat().st_size

        if original_size <= MAX_IMAGE_SIZE:
            b64_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
            return b64_data, original_size

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        target_size = MAX_IMAGE_SIZE

        for scale in [1.0, 0.5, 0.25, 0.1]:
            if scale < 1.0:
                current_img = img.resize(
                    (int(img.size[0] * scale), int(img.size[1] * scale)),
                    Image.LANCZOS
                )
            else:
                current_img = img

            for quality in [85, 70, 55, 40, 30]:
                buffer = io.BytesIO()
                current_img.save(buffer, format="JPEG", quality=quality, optimize=True)
                compressed_size = buffer.tell()

                if compressed_size <= target_size:
                    b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    return b64_data, compressed_size

        buffer = io.BytesIO()
        img.resize((int(img.size[0] * 0.1), int(img.size[1] * 0.1)), Image.LANCZOS).save(
            buffer, format="JPEG", quality=20, optimize=True
        )
        b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return b64_data, buffer.tell()
    except Exception as e:
        logger.error("图片压缩失败: %s", e)
        return None


def read_image_as_base64(image_path: Path) -> str | None:
    if not image_path.exists():
        logger.error("图片文件不存在: %s", image_path)
        return None
    suffix = image_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        logger.error("不支持的图片格式: %s，仅支持: %s", suffix, ", ".join(SUPPORTED_SUFFIXES))
        return None
    result = compress_image_to_base64(image_path)
    if result:
        b64_data, compressed_size = result
        logger.info("  原始: %.2fMB -> 压缩后: %.2fKB",
                   image_path.stat().st_size / 1024 / 1024, compressed_size / 1024)
    return result[0] if result else None


def validate_operation(op: dict, index: int) -> str | None:
    valid_ops = {"create", "update", "delete"}
    operation = op.get("operation", "")
    if operation not in valid_ops:
        return f"操作 {index + 1}: 无效的 operation '{operation}'，必须是 {valid_ops}"

    if operation == "delete":
        if not op.get("media_id"):
            return f"操作 {index + 1}: delete 操作缺少 media_id"
        return None

    if operation in {"create", "update"}:
        if not op.get("image_name"):
            return f"操作 {index + 1}: {operation} 操作缺少 image_name"
        if not op.get("category"):
            return f"操作 {index + 1}: {operation} 操作缺少 category"
        if operation == "update" and not op.get("media_id"):
            return f"操作 {index + 1}: update 操作缺少 media_id"
        if not op.get("image_path"):
            return f"操作 {index + 1}: {operation} 操作缺少 image_path"
    return None


def resolve_image_path(relative_path: str) -> Path:
    data_dir = SCRIPT_DIR / "data"
    if relative_path.startswith("images/"):
        return data_dir / relative_path
    return data_dir / "images" / relative_path


def execute_operation(op: dict, index: int, total: int) -> bool:
    operation = op["operation"]
    image_name = op.get("image_name", "")
    category = op.get("category", "")
    media_id = op.get("media_id")
    image_path = op.get("image_path", "")

    logger.info("执行 [%d/%d] %s: %s (%s)",
                index + 1, total, operation.upper(),
                image_name or f"media_id={media_id}", category or "")

    form_data: dict = {"operation": operation, "api_key": REMOTE_API_KEY}

    if operation in {"create", "update"}:
        resolved_path = resolve_image_path(image_path)
        b64_data = read_image_as_base64(resolved_path)
        if not b64_data:
            return False
        form_data["image_name"] = image_name
        form_data["category"] = category
        form_data["base64_data"] = b64_data

    if operation == "update":
        form_data["media_id"] = media_id

    if operation == "delete":
        form_data["media_id"] = media_id

    try:
        with httpx.Client(timeout=60, verify=False) as client:
            response = client.post(REMOTE_API_URL, data=form_data)
        result = response.json()

        if result.get("success"):
            logger.info("  ✓ 成功: media_id=%s", result.get("media_id", ""))
            return True
        else:
            logger.error("  ✗ 失败: %s", result.get("error", "未知错误"))
            return False
    except httpx.HTTPError as e:
        logger.error("  ✗ 请求失败: %s", e)
        return False
    except Exception:
        logger.exception("  ✗ 异常")
        return False


def main(config_path: Path) -> None:
    config = load_config(config_path)
    operations = config.get("operations", [])

    if not operations:
        logger.warning("没有配置任何操作，请检查 %s", config_path)
        return

    for i, op in enumerate(operations):
        error = validate_operation(op, i)
        if error:
            logger.error(error)
            sys.exit(1)

    logger.info("共 %d 个操作，开始执行...", len(operations))
    logger.info("远程服务器: %s", REMOTE_API_URL)

    results: list[bool] = []
    for i, op in enumerate(operations):
        ok = execute_operation(op, i, len(operations))
        results.append(ok)

    success = sum(1 for r in results if r)
    fail = len(results) - success
    logger.info("完成：成功 %d，失败 %d", success, fail)

    if fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量处理参访方案图片的增删改操作")
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=str(OPS_FILE),
        help=f"配置文件路径 (默认: {OPS_FILE})"
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    main(config_path)