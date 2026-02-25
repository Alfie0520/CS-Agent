import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Query, Request, Response
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.core.security import check_signature
from app.core.xml_parser import build_transfer_kf_xml, parse_xml
from app.handler.router import dispatch
from app.models.message import MsgType
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
