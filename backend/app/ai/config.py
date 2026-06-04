"""
AI Agent 配置管理。

所有 Agent 相关配置集中在此，通过 Pydantic Settings 从环境变量 / .env 加载。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import settings as main_settings


class AISettings(BaseSettings):
    """AI 模块全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- DeepSeek API ----
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_TEMPERATURE: float = 0.7
    DEEPSEEK_MAX_TOKENS: int = 4096

    # ---- Agent 通用 ----
    AGENT_MAX_ITERATIONS: int = 10
    AGENT_VERBOSE: bool = True

    # ---- Memory ----
    MEMORY_MAX_TOKENS: int = 4000
    MEMORY_WINDOW_SIZE: int = 20  # 短期记忆保留最近 N 轮对话

    # ---- 转人工 ----
    CONFIDENCE_THRESHOLD: float = 0.3  # 知识库检索最高分低于此值时自动转人工

    # ---- LangGraph ----
    GRAPH_MAX_STEPS: int = 50


ai_settings = AISettings()

# 如果 AI 模块没配置 API Key，回退到主配置的 DEEPSEEK_API_KEY
if not ai_settings.DEEPSEEK_API_KEY and main_settings.DEEPSEEK_API_KEY:
    ai_settings.DEEPSEEK_API_KEY = main_settings.DEEPSEEK_API_KEY
