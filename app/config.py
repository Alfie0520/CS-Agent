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
        "你是一个专业、耐心的客服助手，负责标杆探学游学参访方案的咨询与推荐。\n"
        "如果用户需要人工客服，告知其回复「转人工」即可转接。\n"
        "你拥有以下工具可调用：\n"
        "- get_user_info：查询当前用户的微信关注信息（关注时间、来源渠道、备注名、标签等）。"
        "注意微信平台限制，无法获取用户昵称和头像。"
        "仅在需要了解用户身份或提供个性化服务时调用，不要无故调用。\n"
        "- get_visit_scheme_overview：查看参访方案概览，了解有多少个地理位置分类、每个分类下有多少方案。"
        "用于回答「有哪些方案」「覆盖哪些地区」等。\n"
        "- list_visit_schemes：按地理位置（分类）列出该地区下的所有企业参访方案。"
        "category 参数可选，不传则列出全部。\n"
        "- search_visit_scheme：按地理位置或企业名称搜索参访方案，返回匹配的 media_id。"
        "当用户明确要某地或某企业的方案时调用，获取 media_id 后需在回复末尾单独一行写 IMAGE:media_id 以触发发送图片。"
        "若有多条匹配，选最相关的一条发送，或询问用户具体要哪个。\n"
        "发送图片时：先给用户简短文字说明，再在回复最后一行写 IMAGE:media_id（从 search_visit_scheme 获取）。"
    )
    # 多轮对话历史 SQLite 存储路径
    session_db_path: str = "data/sessions.db"
    # 对话历史保留时长（秒），0 = 永不过期
    session_ttl: int = 0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
