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

    # 运行时业务数据路径：用于脱离代码发布更新参访方案和媒体资产
    enterprise_data_path: str = "/data/cs-agent-data/enterprises.json"
    asset_root_path: str = "/data/cs-agent-assets"
    asset_index_path: str = "/data/cs-agent-assets/asset_index.json"
    asset_delivery_cache_path: str = "/data/cs-agent-assets/delivery_cache.json"

    # 微信自定义菜单配置文件路径，仅在显式开启启动发布时使用
    wechat_menu_file_path: str = "wechat_menu.json"
    # 是否在服务启动时自动发布本地菜单配置到微信
    wechat_menu_auto_create_on_startup: bool = False
    # 菜单管理 API 访问密钥
    menu_api_key: str = ""

    # ---- 微信客服 (KF) 渠道 ----
    kf_enabled: bool = False
    kf_corp_id: str = ""
    kf_secret: str = ""
    kf_token: str = ""
    kf_encoding_aes_key: str = ""
    kf_api_base_url: str = "https://qyapi.weixin.qq.com"
    kf_open_kfid: str = ""  # 客服账号 ID

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def should_auto_create_wechat_menu_on_startup(self) -> bool:
        return self.wechat_menu_auto_create_on_startup and bool(
            self.wechat_menu_file_path
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
