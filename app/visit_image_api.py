"""参访方案图片增删改 API。

提供统一的接口处理图片的完整更新流程：
- 新增：上传到微信 → 获取 media_id → 写入索引
- 更新：查询旧记录 → 删除微信旧素材 → 上传新图片 → 更新索引
- 删除：从微信删除素材 → 从索引移除
"""

from __future__ import annotations

import base64
import logging
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

from app.media_index import delete as delete_from_index
from app.media_index import exists, get_by_media_id, upsert
from app.wechat_api.material import add_material_image, delete_material_image

logger = logging.getLogger(__name__)

_TEMP_DIR = Path("data/temp_images")
_SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}


class ImageOperation(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


async def _save_base64_to_temp(base64_data: str, suffix: str) -> Path | None:
    """将 base64 数据保存到临时目录，返回文件路径。"""
    _TEMP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        image_bytes = base64.b64decode(base64_data)
    except Exception:
        logger.error("Invalid base64 data")
        return None
    file_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = _TEMP_DIR / file_name
    file_path.write_bytes(image_bytes)
    return file_path


def _validate_params(
    operation: str,
    image_name: str | None,
    category: str | None,
    base64_data: str | None,
    media_id: str | None,
) -> str | None:
    """校验参数，返回错误信息或 None（校验通过）。"""
    if operation not in [ImageOperation.CREATE.value, ImageOperation.UPDATE.value, ImageOperation.DELETE.value]:
        return f"Invalid operation: {operation}"

    if operation == ImageOperation.DELETE:
        if not media_id:
            return "media_id is required for delete operation"
        return None

    if operation in [ImageOperation.CREATE.value, ImageOperation.UPDATE.value]:
        if not image_name:
            return "image_name is required"
        if not category:
            return "category is required"
        if not base64_data:
            return "base64_data is required"
        if not _is_valid_image_suffix(image_name):
            return f"Unsupported image suffix. Supported: {', '.join(_SUPPORTED_SUFFIXES)}"

    return None


def _is_valid_image_suffix(image_name: str) -> bool:
    """检查图片后缀是否支持。"""
    suffix = Path(image_name).suffix.lower()
    return suffix in _SUPPORTED_SUFFIXES


async def _do_create(
    image_name: str, category: str, base64_data: str
) -> dict[str, Any]:
    """执行新增图片流程。"""
    suffix = Path(image_name).suffix.lower()
    file_path = await _save_base64_to_temp(base64_data, suffix)
    if not file_path:
        return {"success": False, "error": "Failed to save image from base64"}

    result = await add_material_image(file_path)
    file_path.unlink(missing_ok=True)

    if "media_id" not in result:
        return {"success": False, "error": f"WeChat API error: {result.get('errmsg', 'unknown')}"}

    media_id = result["media_id"]
    upsert(media_id, image_name, category)
    logger.info("[CREATE] %s (%s) -> media_id=%s", image_name, category, media_id)

    return {
        "success": True,
        "operation": ImageOperation.CREATE.value,
        "media_id": media_id,
        "image_name": image_name,
        "category": category,
    }


async def _do_update(
    media_id: str, image_name: str, category: str, base64_data: str
) -> dict[str, Any]:
    """执行更新图片流程。

    顺序：先上传新素材 → 再删除旧素材 → 最后更新索引。
    任何步骤失败都会回退，保证线上不受影响。
    """
    old_record = get_by_media_id(media_id)
    if not old_record:
        return {"success": False, "error": f"media_id {media_id} not found in index"}

    suffix = Path(image_name).suffix.lower()
    file_path = await _save_base64_to_temp(base64_data, suffix)
    if not file_path:
        return {"success": False, "error": "Failed to save image from base64"}

    result = await add_material_image(file_path)
    file_path.unlink(missing_ok=True)

    if "media_id" not in result:
        return {"success": False, "error": f"WeChat upload failed: {result.get('errmsg', 'unknown')}"}

    new_media_id = result["media_id"]

    delete_result = await delete_material_image(media_id)
    if delete_result.get("errcode", 0) != 0:
        return {
            "success": False,
            "error": f"Old image deletion failed (new image already uploaded to WeChat): {delete_result}",
            "new_media_id": new_media_id,
        }

    delete_from_index(media_id)
    upsert(new_media_id, image_name, category)
    logger.info("[UPDATE] %s (%s): %s -> %s", image_name, category, media_id, new_media_id)

    return {
        "success": True,
        "operation": ImageOperation.UPDATE.value,
        "old_media_id": media_id,
        "new_media_id": new_media_id,
        "image_name": image_name,
        "category": category,
    }


async def _do_delete(media_id: str) -> dict[str, Any]:
    """执行删除图片流程：从微信删除素材，从索引移除。"""
    old_record = get_by_media_id(media_id)
    if not old_record:
        return {"success": False, "error": f"media_id {media_id} not found in index"}

    delete_result = await delete_material_image(media_id)
    if delete_result.get("errcode", 0) != 0:
        return {"success": False, "error": f"Failed to delete from WeChat: {delete_result}"}

    delete_from_index(media_id)
    image_name = old_record.get("image_name", "")
    category = old_record.get("category", "")
    logger.info("[DELETE] %s (%s): media_id=%s", image_name, category, media_id)

    return {
        "success": True,
        "operation": ImageOperation.DELETE.value,
        "media_id": media_id,
        "image_name": image_name,
        "category": category,
    }


async def process_image_operation(
    operation: str,
    image_name: str | None = None,
    category: str | None = None,
    base64_data: str | None = None,
    media_id: str | None = None,
) -> dict[str, Any]:
    """处理参访方案图片的增删改操作。

    Args:
        operation: 操作类型，"create" | "update" | "delete"
        image_name: 图片文件名（如 "胖东来.png"），create/update 时必填
        category: 分类/地理位置（如 "09河南"），create/update 时必填
        base64_data: 图片的 base64 编码字符串，create/update 时必填
        media_id: 要操作的素材 media_id，update/delete 时必填

    Returns:
        {
            "success": bool,
            "operation": str,
            "media_id": str (新增/更新后),
            "image_name": str,
            "category": str,
            "error": str (失败时)
        }
    """
    error = _validate_params(operation, image_name, category, base64_data, media_id)
    if error:
        return {"success": False, "error": error}

    if operation == ImageOperation.CREATE.value:
        return await _do_create(image_name, category, base64_data)
    elif operation == ImageOperation.UPDATE.value:
        return await _do_update(media_id, image_name, category, base64_data)
    else:
        return await _do_delete(media_id)