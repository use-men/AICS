"""
TicketService — 工单分类服务。

对外暴露的业务接口，供 API 层调用。
"""

import json
import logging

from pydantic import BaseModel, Field

from app.ai.manager import agent_manager
from app.ai.agents.ticket_classifier import TICKET_TYPES

logger = logging.getLogger(__name__)


# ---- 请求 / 响应模型 ----

class ClassifyRequest(BaseModel):
    """工单分类请求"""
    title: str = Field(..., min_length=1, max_length=200, description="工单标题")
    content: str = Field(..., min_length=1, max_length=5000, description="工单内容")


class ClassifyResponse(BaseModel):
    """工单分类响应"""
    ticket_type: str = Field(..., description="工单类型 key")
    ticket_type_name: str = Field(..., description="工单类型中文名")
    confidence: float = Field(..., ge=0, le=1, description="置信度 0~1")


# ---- 服务 ----

class TicketService:
    """工单分类服务"""

    def __init__(self):
        self._register_agent()

    def _register_agent(self):
        """注册工单分类 Agent"""
        from app.ai.agents.ticket_classifier import TicketClassificationAgent
        agent = TicketClassificationAgent()
        agent_manager.register(agent)

    async def classify(self, req: ClassifyRequest) -> ClassifyResponse:
        """
        分类工单。

        Args:
            req: 分类请求（标题+内容）

        Returns:
            分类结果
        """
        # 构造输入
        input_text = json.dumps({
            "title": req.title,
            "content": req.content,
        }, ensure_ascii=False)

        # 调用 Agent
        raw = await agent_manager.invoke("ticket_classifier", input_text)

        # 解析结果
        result = json.loads(raw)
        ticket_type = result.get("ticket_type", "after_sales")
        confidence = result.get("confidence", 0.5)

        return ClassifyResponse(
            ticket_type=ticket_type,
            ticket_type_name=TICKET_TYPES.get(ticket_type, "售后咨询"),
            confidence=confidence,
        )


# ---- 全局单例 ----

ticket_service = TicketService()
