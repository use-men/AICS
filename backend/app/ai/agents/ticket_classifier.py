"""
TicketClassificationAgent — 工单自动分类 Agent。

接收工单标题+内容，输出分类结果和置信度。
"""

import json
import logging
from typing import Any, AsyncIterator

from app.ai.agents.base import BaseAgent
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
    def system_prompt(self) -> str:
        return TICKET_CLASSIFICATION_SYSTEM

    @property
    def _temperature(self) -> float:
        return 0.1  # 分类任务需要低温度，保证稳定性

    async def invoke(self, input_text: str, **kwargs: Any) -> str:
        """
        同步分类工单。

        Args:
            input_text: JSON 字符串，包含 title 和 content
            **kwargs: 额外参数

        Returns:
            JSON 字符串，包含 ticket_type 和 confidence
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": input_text},
        ]
        try:
            response = await self.llm.ainvoke(messages)
            return self._parse_response(response.content)
        except Exception as e:
            logger.error("[TicketClassifier] 调用失败: %s", e)
            return json.dumps(DEFAULT_RESULT, ensure_ascii=False)

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
