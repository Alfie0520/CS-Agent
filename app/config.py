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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
