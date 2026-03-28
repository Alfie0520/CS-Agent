import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Query, Request, Response
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.core.security import check_signature
from app.core.xml_parser import build_transfer_kf_xml, parse_xml
from app.handler.router import dispatch
from app.models.message import MsgType
from app.visit_image_api import ImageOperation, process_image_operation
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
    operation: str,
    image_name: str | None = None,
    category: str | None = None,
    base64_data: str | None = None,
    media_id: str | None = None,
    api_key: str | None = None,
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
