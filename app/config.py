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
    
    # 动态提示词配置
    prompt_base_role_path: str = "app/prompts/base_role.md"
    prompt_strict_rules_path: str = "app/prompts/strict_rules.md"
    # 公司老板微信二维码 media_id（用于 get_wechat_qr_code 工具）
    wechat_qr_code_media_id: str = ""

    # 多轮对话历史 SQLite 存储路径
    session_db_path: str = "/data/sessions.db"
    # 对话历史保留时长（秒），0 = 永不过期
    session_ttl: int = 0

    # 参访图片 API 访问密钥
    visit_image_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
