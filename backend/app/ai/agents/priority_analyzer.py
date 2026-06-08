"""
PriorityAnalyzerAgent — 工单优先级分析 Agent。

根据工单内容、用户等级、历史投诉次数，输出优先级和原因。
"""

import json
import logging
from typing import Any, AsyncIterator

from app.ai.agents.base import BaseAgent
from app.ai.schemas import AgentState, AgentType, TaskStatus
from app.ai.prompts.templates import PRIORITY_SYSTEM

logger = logging.getLogger(__name__)

# ---- 优先级映射 ----

PRIORITY_LEVELS = {"urgent", "high", "medium", "low"}

DEFAULT_RESULT = {"priority": "medium", "reason": "默认中等优先级"}


class PriorityAnalyzerAgent(BaseAgent):
    """工单优先级分析 Agent"""

    @property
    def agent_name(self) -> str:
        return "priority_analyzer"

    @property
    def agent_type(self) -> AgentType:
        return AgentType.PRIORITY_ANALYZER

    @property
    def system_prompt(self) -> str:
        return PRIORITY_SYSTEM

    @property
    def _temperature(self) -> float:
        return 0.1

    # ---- 核心接口（统一入口） ----

    async def run(self, state: AgentState) -> AgentState:
        """
        统一执行入口。

        Args:
            state: 当前 Agent 状态，需要包含 user_input（JSON 格式的工单信息）

        Returns:
            更新后的 Agent 状态，包含 ticket_priority
        """
        state.agent_type = self.agent_type
        state.status = TaskStatus.PROCESSING

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": state.user_input},
            ]
            response = await self.llm.ainvoke(messages)
            result = self._parse_response(response.content)

            # 解析结果
            result_data = json.loads(result)
            state.ticket_priority = result_data.get("priority", "medium")
            state.metadata["priority_reason"] = result_data.get("reason", "无")

            state.status = TaskStatus.COMPLETED

        except Exception as e:
            logger.error("[PriorityAnalyzer] 调用失败: %s", e)
            state.error = str(e)
            state.status = TaskStatus.FAILED
            state.ticket_priority = "medium"  # 默认优先级

        return state

    # ---- 兼容旧接口 ----

    async def invoke(self, input_text: str, **kwargs: Any) -> str:
        """
        分析工单优先级（兼容旧接口）。

        Args:
            input_text: JSON 字符串，包含 title, content, user_level, complaint_count
            **kwargs: 额外参数

        Returns:
            JSON 字符串，包含 priority 和 reason
        """
        state = self._create_state(input_text, **kwargs)
        state = await self.run(state)

        return json.dumps({
            "priority": state.ticket_priority,
            "reason": state.metadata.get("priority_reason", "无"),
        }, ensure_ascii=False)

    async def stream(self, input_text: str, **kwargs: Any) -> AsyncIterator[str]:
        result = await self.invoke(input_text, **kwargs)
        yield result

    def _parse_response(self, raw: str) -> str:
        """解析 LLM 返回的 JSON"""
        try:
            text = raw.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            result = json.loads(text)

            priority = result.get("priority", "medium")
            reason = result.get("reason", "无")

            if priority not in PRIORITY_LEVELS:
                priority = "medium"

            return json.dumps({
                "priority": priority,
                "reason": reason,
            }, ensure_ascii=False)

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("[PriorityAnalyzer] JSON 解析失败: %s | raw: %s", e, raw[:200])
            return json.dumps(DEFAULT_RESULT, ensure_ascii=False)
