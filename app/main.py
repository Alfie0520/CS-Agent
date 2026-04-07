import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Form, Query, Request, Response
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.core.security import check_signature
from app.core.xml_parser import build_transfer_kf_xml, parse_xml
from app.handler.router import dispatch
from app.models.message import MsgType
from app.visit_image_api import ImageOperation, process_image_operation
from app.wechat_api.menu import (
    add_conditional_menu,
    create_menu,
    create_menu_from_json_file,
    del_conditional_menu,
    delete_menu,
    get_current_selfmenu_info,
    get_menu,
    try_match_menu,
)
from app.wechat_api.token_manager import token_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    await token_manager.start()
    logger.info("CS-Agent started")

    menu_file = settings.wechat_menu_file_path
    if menu_file:
        logger.info("Auto-creating WeChat menu from: %s", menu_file)
        result = await create_menu_from_json_file(menu_file)
        if result.get("errcode", 0) == 0:
            logger.info("WeChat menu created successfully")
        else:
            logger.warning("Failed to create WeChat menu: %s", result)

    yield
    await token_manager.stop()
    logger.info("CS-Agent stopped")


app = FastAPI(title="CS-Agent", lifespan=lifespan)


@app.get("/wx", response_class=PlainTextResponse)
async def verify_token(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    """微信服务器首次配置验证：校验签名后原样返回 echostr。"""
    settings = get_settings()
    if check_signature(signature, timestamp, nonce, settings.wechat_token):
        return echostr
    return "invalid signature"


@app.post("/wx")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """接收微信推送的消息/事件。
    - 转人工客服：同步返回 transfer_customer_service XML（仅此场景需要被动回复）
    - 其他消息：立即返回 success，异步通过客服消息接口回复
    """
    body = await request.body()

    try:
        msg = parse_xml(body)
        if (
            msg.msg_type == MsgType.TEXT
            and (msg.content or "").strip() == "转人工"
        ):
            xml = build_transfer_kf_xml(
                to_user=msg.from_user, from_user=msg.to_user
            )
            return Response(content=xml, media_type="application/xml")
    except Exception:
        logger.exception("Failed to check passive reply condition")

    background_tasks.add_task(dispatch, body)
    return PlainTextResponse("success")


@app.post("/api/visit-image")
async def manage_visit_image(
    operation: str = Form(...),
    image_name: str | None = Form(None),
    category: str | None = Form(None),
    base64_data: str | None = Form(None),
    media_id: str | None = Form(None),
    api_key: str | None = Form(None),
):
    """参访方案图片增删改接口。

    完整流程：上传到微信服务器 → 获取 media_id → 更新索引（删除旧记录）→ 返回结果

    Args:
        operation: 操作类型，"create" | "update" | "delete"
        image_name: 图片文件名（如 "胖东来.png"），create/update 时必填
        category: 分类/地理位置（如 "09河南"），create/update 时必填
        base64_data: 图片的 base64 编码字符串，create/update 时必填
        media_id: 要操作的素材 media_id，update/delete 时必填
        api_key: API 访问密钥，必须与环境变量中的 API_KEY 匹配

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
    settings = get_settings()
    expected_key = getattr(settings, "visit_image_api_key", None)
    if expected_key and api_key != expected_key:
        return {"success": False, "error": "Invalid API key"}

    result = await process_image_operation(
        operation=operation,
        image_name=image_name,
        category=category,
        base64_data=base64_data,
        media_id=media_id,
    )
    return result


@app.post("/api/menu")
async def manage_menu(
    operation: str = Form(...),
    menu_file_path: str | None = Form(None),
    menu_data: str | None = Form(None),
    api_key: str | None = Form(None),
):
    """自定义菜单增删改查接口（供 Postman 调用）。

    Args:
        operation: 操作类型
            - "create": 从文件或 JSON 创建菜单（默认）
            - "get": 查询当前菜单配置
            - "delete": 删除当前菜单
            - "get_selfmenu": 获取当前使用的自定义菜单配置
            - "create_conditional": 创建个性化菜单（需传 menu_data）
            - "delete_conditional": 删除个性化菜单（需传 menu_data 中的 menuid）
            - "try_match": 测试个性化菜单匹配（需传 menu_data 中的 user_id）
        menu_file_path: 菜单 JSON 文件路径，operation=create 时使用（优先级高于 menu_data）
        menu_data: JSON 字符串，个性化菜单操作时需要传入
        api_key: API 访问密钥，必须与环境变量中的 API_KEY 匹配

    Returns:
        微信 API 的原始响应 JSON
    """
    settings = get_settings()
    expected_key = getattr(settings, "visit_image_api_key", None)
    if expected_key and api_key != expected_key:
        return {"success": False, "error": "Invalid API key"}

    if operation == "get":
        return await get_menu()
    elif operation == "delete":
        return await delete_menu()
    elif operation == "get_selfmenu":
        return await get_current_selfmenu_info()
    elif operation == "create_conditional":
        if not menu_data:
            return {"success": False, "error": "个性化菜单创建需要传入 menu_data"}
        import json
        return await add_conditional_menu(json.loads(menu_data))
    elif operation == "delete_conditional":
        if not menu_data:
            return {"success": False, "error": "删除个性化菜单需要传入 menu_data"}
        import json
        return await del_conditional_menu(json.loads(menu_data)["menuid"])
    elif operation == "try_match":
        if not menu_data:
            return {"success": False, "error": "测试个性化菜单匹配需要传入 menu_data"}
        import json
        return await try_match_menu(json.loads(menu_data)["user_id"])
    elif operation == "create":
        if menu_file_path:
            return await create_menu_from_json_file(menu_file_path)
        elif menu_data:
            import json
            return await create_menu(json.loads(menu_data))
        else:
            return {"success": False, "error": "创建菜单需要传入 menu_file_path 或 menu_data"}
    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}

