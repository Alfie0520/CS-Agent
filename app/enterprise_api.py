"""内部企业参访数据管理 API。"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile

from app.config import get_settings
from app.enterprise_data import load_enterprises, save_enterprises

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
    return {"success": True, "count": len(items), "items": items}


@router.post("/data")
async def upload_enterprise_data(
    json_file: UploadFile = File(...),
    api_key: str | None = Form(None),
) -> dict[str, Any]:
    error = _check_api_key(api_key)
    if error:
        return error

    try:
        data = json.loads((await json_file.read()).decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": f"Invalid JSON: {e}"}

    if not isinstance(data, list):
        return {"success": False, "error": "Enterprise data must be a JSON array"}

    save_enterprises(data)
    return {"success": True, "count": len(data)}
