"""
TicketClassificationAgent — 工单自动分类 Agent。

接收工单标题+内容，输出分类结果和置信度。
"""

import json
import logging
from typing import Any, AsyncIterator

from app.ai.agents.base import BaseAgent
from app.ai.schemas import AgentState, AgentType, TaskStatus
from app.ai.prompts.templates import TICKET_CLASSIFICATION_SYSTEM

logger = logging.getLogger(__name__)

# ---- 分类映射 ----

TICKET_TYPES = {
    "after_sales": "售后咨询",
    "technical": "技术支持",
    "refund": "退款申请",
    "complaint": "投诉建议",
}

DEFAULT_RESULT = {"ticket_type": "after_sales", "confidence": 0.5}


class TicketClassificationAgent(BaseAgent):
    """工单分类 Agent"""

    @property
    def agent_name(self) -> str:
        return "ticket_classifier"

    @property
    def agent_type(self) -> AgentType:
        return AgentType.TICKET_CLASSIFIER

    @property
    def system_prompt(self) -> str:
        return TICKET_CLASSIFICATION_SYSTEM

    @property
    def _temperature(self) -> float:
        return 0.1  # 分类任务需要低温度，保证稳定性

    # ---- 核心接口（统一入口） ----

    async def run(self, state: AgentState) -> AgentState:
        """
        统一执行入口。

        Args:
            state: 当前 Agent 状态，需要包含 user_input（JSON 格式的 title 和 content）

        Returns:
            更新后的 Agent 状态，包含 ticket_type
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
            state.ticket_type = result_data.get("ticket_type", "after_sales")
            state.metadata["classification_confidence"] = result_data.get("confidence", 0.5)

            state.status = TaskStatus.COMPLETED

        except Exception as e:
            logger.error("[TicketClassifier] 调用失败: %s", e)
            state.error = str(e)
            state.status = TaskStatus.FAILED
            state.ticket_type = "after_sales"  # 默认分类

        return state

    # ---- 兼容旧接口 ----

    async def invoke(self, input_text: str, **kwargs: Any) -> str:
        """
        同步分类工单（兼容旧接口）。

        Args:
            input_text: JSON 字符串，包含 title 和 content
            **kwargs: 额外参数

        Returns:
            JSON 字符串，包含 ticket_type 和 confidence
        """
        state = self._create_state(input_text, **kwargs)
        state = await self.run(state)

        return json.dumps({
            "ticket_type": state.ticket_type,
            "confidence": state.metadata.get("classification_confidence", 0.5),
        }, ensure_ascii=False)

    async def stream(self, input_text: str, **kwargs: Any) -> AsyncIterator[str]:
        """流式分类（分类任务通常不需要流式，这里简单实现）"""
        result = await self.invoke(input_text, **kwargs)
        yield result

    def _parse_response(self, raw: str) -> str:
        """解析 LLM 返回的 JSON"""
        try:
            # 尝试提取 JSON 部分
            text = raw.strip()
            # 处理可能被 markdown 包裹的情况
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            result = json.loads(text)

            # 校验字段
            ticket_type = result.get("ticket_type", "after_sales")
            confidence = float(result.get("confidence", 0.5))

            # 校验 ticket_type 合法性
            if ticket_type not in TICKET_TYPES:
                ticket_type = "after_sales"

            # 校验 confidence 范围
            confidence = max(0.0, min(1.0, confidence))

            return json.dumps({
                "ticket_type": ticket_type,
                "confidence": round(confidence, 2),
            }, ensure_ascii=False)

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("[TicketClassifier] JSON 解析失败: %s | raw: %s", e, raw[:200])
            return json.dumps(DEFAULT_RESULT, ensure_ascii=False)
