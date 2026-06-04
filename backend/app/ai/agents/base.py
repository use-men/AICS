"""
BaseAgent — 所有 Agent 的抽象基类。

职责:
    1. 定义 Agent 统一接口
    2. 管理 LLM 实例、工具列表、Prompt 模板
    3. 提供 invoke / stream 标准调用方式
    4. 集成 Memory 管理
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.ai.config import ai_settings
from app.ai.llm import get_llm_for_agent

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Agent 抽象基类。

    子类必须实现:
        - agent_name: 唯一标识名
        - system_prompt: 系统提示词
        - build_agent(): 构建 Agent 执行链（LangChain Chain / LangGraph Graph）

    子类可选覆盖:
        - tools: 工具列表
        - llm: 自定义 LLM 实例
    """

    # ---- 子类必须定义 ----

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Agent 唯一名称，如 'qa_agent', 'ticket_router'"""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """系统提示词"""
        ...

    # ---- 子类可选覆盖 ----

    @property
    def tools(self) -> list[BaseTool]:
        """Agent 可使用的工具列表"""
        return []

    @property
    def llm(self) -> BaseChatModel:
        """Agent 使用的 LLM 实例"""
        if self._llm is None:
            self._llm = get_llm_for_agent(temperature=self._temperature)
        return self._llm

    @property
    def _temperature(self) -> float:
        """生成温度，子类可覆盖"""
        return ai_settings.DEEPSEEK_TEMPERATURE

    # ---- 初始化 ----

    def __init__(self, **kwargs: Any):
        self._config = kwargs
        self._llm: BaseChatModel = get_llm_for_agent(temperature=self._temperature)
        logger.info("[Agent] 初始化: %s", self.agent_name)

    # ---- 核心接口 ----

    @abstractmethod
    async def invoke(self, input_text: str, **kwargs: Any) -> str:
        """
        同步调用 Agent，返回最终文本结果。

        Args:
            input_text: 用户输入
            **kwargs: 额外参数（如 conversation_id, user_id）

        Returns:
            Agent 的文本响应
        """
        ...

    @abstractmethod
    async def stream(self, input_text: str, **kwargs: Any) -> AsyncIterator[str]:
        """
        流式调用 Agent，逐步 yield 文本片段。

        Args:
            input_text: 用户输入
            **kwargs: 额外参数

        Yields:
            文本片段
        """
        ...

    # ---- 辅助方法 ----

    def build_messages(self, user_input: str, history: list[BaseMessage] | None = None) -> list[BaseMessage]:
        """
        构建消息列表（系统提示 + 历史 + 用户输入）。

        Args:
            user_input: 用户输入
            history: 对话历史

        Returns:
            消息列表
        """
        messages: list[BaseMessage] = [SystemMessage(content=self.system_prompt)]
        if history:
            messages.extend(history)
        messages.append(HumanMessage(content=user_input))
        return messages

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.agent_name}>"
