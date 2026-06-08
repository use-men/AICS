"""
AgentManager — Agent 生命周期管理器。

职责:
    1. 注册 / 注销 Agent
    2. 按名称获取 Agent 实例
    3. 统一调用入口（run / invoke / stream）
    4. 健康检查
"""

import logging
from typing import Any, AsyncIterator

from app.ai.agents.base import BaseAgent
from app.ai.schemas import AgentState

logger = logging.getLogger(__name__)


class AgentManager:
    """
    全局 Agent 管理器（单例模式）。

    使用方式:
        manager = AgentManager()
        manager.register(my_agent)
        result = await manager.invoke("qa_agent", "什么是工单？")
    """

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    # ---- 注册 / 注销 ----

    def register(self, agent: BaseAgent) -> None:
        """注册一个 Agent 实例"""
        name = agent.agent_name
        if name in self._agents:
            logger.warning("[AgentManager] 覆盖注册: %s", name)
        self._agents[name] = agent
        logger.info("[AgentManager] 注册 Agent: %s (%s)", name, agent.__class__.__name__)

    def unregister(self, agent_name: str) -> None:
        """注销一个 Agent"""
        if agent_name in self._agents:
            del self._agents[agent_name]
            logger.info("[AgentManager] 注销 Agent: %s", agent_name)
        else:
            logger.warning("[AgentManager] 注销失败，Agent 不存在: %s", agent_name)

    # ---- 获取 ----

    def get(self, agent_name: str) -> BaseAgent | None:
        """按名称获取 Agent 实例"""
        return self._agents.get(agent_name)

    def get_or_raise(self, agent_name: str) -> BaseAgent:
        """按名称获取 Agent，不存在则抛出异常"""
        agent = self._agents.get(agent_name)
        if agent is None:
            raise KeyError(f"Agent 不存在: {agent_name}")
        return agent

    @property
    def agent_names(self) -> list[str]:
        """所有已注册的 Agent 名称"""
        return list(self._agents.keys())

    # ---- 调用（新接口） ----

    async def run(self, agent_name: str, state: AgentState) -> AgentState:
        """
        统一执行入口。

        Args:
            agent_name: Agent 名称
            state: 当前 Agent 状态

        Returns:
            更新后的 Agent 状态
        """
        agent = self.get_or_raise(agent_name)
        logger.info("[AgentManager] run: %s | input: %s", agent_name, state.user_input[:100])
        result = await agent.run(state)
        logger.info("[AgentManager] result: %s | status: %s", agent_name, result.status.value)
        return result

    # ---- 调用（兼容旧接口） ----

    async def invoke(self, agent_name: str, input_text: str, **kwargs: Any) -> str:
        """
        调用指定 Agent（兼容旧接口）。

        Args:
            agent_name: Agent 名称
            input_text: 用户输入
            **kwargs: 额外参数

        Returns:
            Agent 的文本响应
        """
        agent = self.get_or_raise(agent_name)
        logger.info("[AgentManager] invoke: %s | input: %s", agent_name, input_text[:100])
        result = await agent.invoke(input_text, **kwargs)
        logger.info("[AgentManager] result: %s | output: %s", agent_name, result[:100])
        return result

    async def stream(self, agent_name: str, input_text: str, **kwargs: Any) -> AsyncIterator[str]:
        """
        流式调用指定 Agent。

        Args:
            agent_name: Agent 名称
            input_text: 用户输入
            **kwargs: 额外参数

        Yields:
            文本片段
        """
        agent = self.get_or_raise(agent_name)
        logger.info("[AgentManager] stream: %s | input: %s", agent_name, input_text[:100])
        async for chunk in agent.stream(input_text, **kwargs):
            yield chunk

    # ---- 健康检查 ----

    def health_check(self) -> dict[str, Any]:
        """返回所有 Agent 的健康状态"""
        return {
            "total": len(self._agents),
            "agents": {
                name: {
                    "class": agent.__class__.__name__,
                    "type": agent.agent_type.value if hasattr(agent, 'agent_type') else "unknown",
                    "tools": [t.name for t in agent.tools],
                }
                for name, agent in self._agents.items()
            },
        }


# ---- 全局单例 ----

agent_manager = AgentManager()
