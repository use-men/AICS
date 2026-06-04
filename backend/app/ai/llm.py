"""
DeepSeek LLM 封装 — 基于 LangChain 的统一调用接口。

使用方式:
    from app.ai.llm import get_llm
    llm = get_llm()
    response = await llm.ainvoke("你好")
"""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.ai.config import ai_settings


@lru_cache(maxsize=1)
def get_llm(
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    """
    获取 DeepSeek ChatOpenAI 实例（单例缓存）。

    Args:
        model: 模型名称，默认从配置读取
        temperature: 生成温度，默认从配置读取
        max_tokens: 最大 token 数，默认从配置读取

    Returns:
        BaseChatModel 实例，兼容 LangChain 生态
    """
    return ChatOpenAI(
        model=model or ai_settings.DEEPSEEK_MODEL,
        openai_api_key=ai_settings.DEEPSEEK_API_KEY,
        openai_api_base=ai_settings.DEEPSEEK_BASE_URL,
        temperature=temperature if temperature is not None else ai_settings.DEEPSEEK_TEMPERATURE,
        max_tokens=max_tokens or ai_settings.DEEPSEEK_MAX_TOKENS,
    )


def get_llm_for_agent(
    model: str | None = None,
    temperature: float = 0.7,
) -> BaseChatModel:
    """
    为 Agent 获取定制化 LLM 实例（不使用缓存，允许不同 Agent 不同参数）。

    Args:
        model: 模型名称
        temperature: 生成温度

    Returns:
        BaseChatModel 实例
    """
    return ChatOpenAI(
        model=model or ai_settings.DEEPSEEK_MODEL,
        openai_api_key=ai_settings.DEEPSEEK_API_KEY,
        openai_api_base=ai_settings.DEEPSEEK_BASE_URL,
        temperature=temperature,
        max_tokens=ai_settings.DEEPSEEK_MAX_TOKENS,
    )
