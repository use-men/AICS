"""
SupervisorAgent — 统一调度 Agent。

职责:
    1. 调度 KnowledgeAgent 进行知识库检索
    2. 判断是否需要转人工
    3. 如果需要转人工，依次调用：
       - TicketClassificationAgent（工单分类）
       - PriorityAnalyzerAgent（优先级分析）
       - TicketCreationAgent（工单创建）
       - DispatchAgent（智能派单）
    4. 记录所有 Agent 的执行日志

执行流程:
    用户提问 → KnowledgeAgent → 判断 → [转人工流程] → 返回结果

使用方式:
    supervisor = SupervisorAgent()
    state = await supervisor.run(state)

内部实现:
    使用 SmartDeskGraph (LangGraph) 进行工作流编排。
"""

import json
import logging
from typing import Any, AsyncIterator

from app.ai.agents.base import BaseAgent
from app.ai.schemas import AgentState, AgentType, TaskStatus
from app.ai.workflows.smartdesk_graph import smartdesk_graph

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """
    统一调度 Agent — 编排所有子 Agent 的执行。

    内部使用 SmartDeskGraph (LangGraph) 进行工作流编排。
    """

    @property
    def agent_name(self) -> str:
        return "supervisor"

    @property
    def agent_type(self) -> AgentType:
        return AgentType.SUPERVISOR

    @property
    def system_prompt(self) -> str:
        return ""  # Supervisor 不需要 LLM

    @property
    def _temperature(self) -> float:
        return 0.0

    # ---- 核心接口（统一入口） ----

    async def run(self, state: AgentState) -> AgentState:
        """
        统一执行入口。

        内部调用 SmartDeskGraph 执行工作流。

        Args:
            state: 当前 Agent 状态

        Returns:
            更新后的 Agent 状态
        """
        state.agent_type = self.agent_type
        state.status = TaskStatus.PROCESSING

        logger.info("[Supervisor] 开始调度 | trace_id: %s | user_input: %s",
                    state.trace_id, state.user_input[:100])

        try:
            # 调用 SmartDeskGraph 执行工作流
            state = await smartdesk_graph.invoke(state)

        except Exception as e:
            logger.error("[Supervisor] 调度失败: %s", e)
            state.error = str(e)
            state.status = TaskStatus.FAILED

        logger.info("[Supervisor] 调度完成 | trace_id: %s | status: %s | total_duration: %.2fms",
                    state.trace_id, state.status.value, state.get_total_duration_ms())

        return state

    # ---- 兼容旧接口 ----

    async def invoke(self, input_text: str, **kwargs: Any) -> str:
        """
        统一调度（兼容旧接口）。

        Args:
            input_text: 用户问题
            **kwargs: user_id, conversation_id

        Returns:
            JSON 字符串，包含完整结果
        """
        state = self._create_state(input_text, **kwargs)
        state = await self.run(state)

        return json.dumps({
            "trace_id": state.trace_id,
            "answer": state.answer,
            "need_human": state.need_human,
            "ticket_type": state.ticket_type,
            "ticket_priority": state.ticket_priority,
            "ticket_id": state.ticket_id,
            "assignee_id": state.assignee_id,
            "status": state.status.value,
            "agent_logs": state.get_agent_summary(),
            "total_duration_ms": state.get_total_duration_ms(),
        }, ensure_ascii=False)

    async def stream(self, input_text: str, **kwargs: Any) -> AsyncIterator[str]:
        """
        流式调度（兼容旧接口）。
        """
        result = await self.invoke(input_text, **kwargs)
        yield result


# ---- 全局单例 ----

supervisor_agent = SupervisorAgent()