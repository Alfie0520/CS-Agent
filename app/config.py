from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    wechat_app_id: str
    wechat_app_secret: str
    wechat_token: str
    wechat_encoding_aes_key: str = ""

    port: int = 80
    log_level: str = "INFO"

    wechat_api_base_url: str = "https://api.weixin.qq.com"

    # MiniMax LLM
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimax.chat/v1"
    minimax_model: str = "MiniMax-Text-01"
    minimax_system_prompt: str = (
        "你是一个专业、耐心的客服助手。请用简洁友好的中文回答用户问题。\n"
        "如果用户需要人工客服，告知其回复「转人工」即可转接。\n"
        "你拥有以下工具可调用：\n"
        "- get_user_info：查询当前用户的微信关注信息（关注时间、来源渠道、备注名、标签等）。"
        "注意微信平台限制，无法获取用户昵称和头像。"
        "仅在需要了解用户身份或提供个性化服务时调用，不要无故调用。"
    )
    # 多轮对话历史 SQLite 存储路径
    session_db_path: str = "data/sessions.db"
    # 对话历史保留时长（秒），0 = 永不过期
    session_ttl: int = 0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
