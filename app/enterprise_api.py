"""内部企业参访数据管理 API。"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile

from app.config import get_settings
from app.enterprise_data import get_data_path, load_enterprises, save_enterprises, validate_enterprises

router = APIRouter(prefix="/api/enterprises", tags=["enterprises"])


def _check_api_key(api_key: str | None) -> dict[str, Any] | None:
    expected_key = get_settings().visit_image_api_key
    if expected_key and api_key != expected_key:
        return {"success": False, "error": "Invalid API key"}
    return None


@router.get("/data")
async def get_enterprise_data(api_key: str | None = None) -> dict[str, Any]:
    error = _check_api_key(api_key)
    if error:
        return error
    items = load_enterprises()
    return {
        "success": True,
        "count": len(items),
        "source_path": str(get_data_path()),
        "items": items,
    }


@router.post("/data")
async def upload_enterprise_data(
    json_file: UploadFile = File(...),
    api_key: str | None = Form(None),
    dry_run: bool = Form(False),
) -> dict[str, Any]:
    error = _check_api_key(api_key)
    if error:
        return error

    try:
        data = json.loads((await json_file.read()).decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": f"Invalid JSON: {e}"}

    try:
        items = validate_enterprises(data)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    if not dry_run:
        save_enterprises(items)
    return {
        "success": True,
        "dry_run": dry_run,
        "count": len(items),
        "target_path": get_settings().enterprise_data_path,
    }
