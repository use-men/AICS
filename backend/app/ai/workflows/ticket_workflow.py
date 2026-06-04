"""
TicketWorkflow — 工单自动流转工作流。

流程: 提交工单 → 分类 → 优先级分析 → 自动派单 → 通知客服
状态: pending → assigned → processing → resolved → closed
"""

import json
import logging
import time
from typing import Any
from dataclasses import dataclass, field

from app.ai.agents.ticket_classifier import TicketClassificationAgent
from app.ai.agents.priority_analyzer import PriorityAnalyzerAgent
from app.ai.agents.dispatcher import dispatch_agent

logger = logging.getLogger(__name__)


# ---- 工单状态定义 ----

class TicketStatus:
    PENDING = "pending"          # 待分配
    ASSIGNED = "assigned"        # 已分配
    PROCESSING = "processing"    # 处理中
    RESOLVED = "resolved"        # 已解决
    CLOSED = "closed"            # 已关闭

    ALL = {PENDING, ASSIGNED, PROCESSING, RESOLVED, CLOSED}

    # 合法的状态流转
    TRANSITIONS = {
        PENDING: {ASSIGNED},
        ASSIGNED: {PROCESSING, PENDING},
        PROCESSING: {RESOLVED, ASSIGNED},
        RESOLVED: {CLOSED, PROCESSING},
        CLOSED: set(),
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        return to_status in cls.TRANSITIONS.get(from_status, set())


# ---- 工作流结果 ----

@dataclass
class WorkflowResult:
    """工作流执行结果"""
    ticket_id: int
    status: str = TicketStatus.PENDING
    ticket_type: str = ""
    type_name: str = ""
    confidence: float = 0.0
    priority: str = ""
    reason: str = ""
    service_id: int | None = None
    service_name: str = ""
    load_ratio: float = 0.0
    steps: list[dict] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "status": self.status,
            "ticket_type": self.ticket_type,
            "type_name": self.type_name,
            "confidence": self.confidence,
            "priority": self.priority,
            "reason": self.reason,
            "service_id": self.service_id,
            "service_name": self.service_name,
            "load_ratio": self.load_ratio,
            "steps": self.steps,
            "error": self.error,
        }


# ---- 分类映射 ----

TICKET_TYPE_NAMES = {
    "after_sales": "售后咨询",
    "technical": "技术支持",
    "refund": "退款申请",
    "complaint": "投诉建议",
}


class TicketWorkflow:
    """
    工单自动流转工作流。

    编排多个 Agent 完成工单的自动处理流程。
    """

    def __init__(self):
        self._classifier = TicketClassificationAgent()
        self._priority_analyzer = PriorityAnalyzerAgent()

    async def run(
        self,
        ticket_id: int,
        title: str,
        content: str,
        user_id: int | None = None,
        user_level: str = "normal",
        complaint_count: int = 0,
    ) -> WorkflowResult:
        """
        执行工单自动流转。

        Args:
            ticket_id: 工单ID
            title: 工单标题
            content: 工单内容
            user_id: 用户ID
            user_level: 用户等级
            complaint_count: 历史投诉次数

        Returns:
            WorkflowResult 工作流结果
        """
        result = WorkflowResult(ticket_id=ticket_id)

        # Step 1: 工单分类
        result = await self._step_classify(result, title, content)
        if result.error:
            return result

        # Step 2: 优先级分析
        result = await self._step_priority(result, title, content, user_level, complaint_count)
        if result.error:
            return result

        # Step 3: 自动派单
        result = await self._step_dispatch(result)
        if result.error:
            return result

        # Step 4: 更新状态为已分配
        result.status = TicketStatus.ASSIGNED
        result.steps.append({
            "step": "status_update",
            "status": TicketStatus.ASSIGNED,
            "message": f"工单已分配给客服: {result.service_name}",
        })

        # Step 5: 通知客服（模拟）
        result = await self._step_notify(result)

        logger.info(
            "[Workflow] 工单 %d 流转完成: type=%s priority=%s service=%s",
            ticket_id, result.ticket_type, result.priority, result.service_name,
        )

        return result

    async def _step_classify(
        self, result: WorkflowResult, title: str, content: str,
    ) -> WorkflowResult:
        """Step 1: 工单分类"""
        try:
            input_text = json.dumps({"title": title, "content": content}, ensure_ascii=False)
            raw = await self._classifier.invoke(input_text)
            data = json.loads(raw)

            result.ticket_type = data.get("ticket_type", "after_sales")
            result.confidence = data.get("confidence", 0.5)
            result.type_name = TICKET_TYPE_NAMES.get(result.ticket_type, "售后咨询")

            result.steps.append({
                "step": "classify",
                "ticket_type": result.ticket_type,
                "type_name": result.type_name,
                "confidence": result.confidence,
                "message": f"工单分类: {result.type_name} (置信度: {result.confidence})",
            })

        except Exception as e:
            logger.error("[Workflow] 分类失败: %s", e)
            result.error = f"分类失败: {str(e)}"
            result.steps.append({"step": "classify", "error": str(e)})

        return result

    async def _step_priority(
        self, result: WorkflowResult, title: str, content: str,
        user_level: str, complaint_count: int,
    ) -> WorkflowResult:
        """Step 2: 优先级分析"""
        try:
            input_text = json.dumps({
                "title": title,
                "content": content,
                "user_level": user_level,
                "complaint_count": complaint_count,
            }, ensure_ascii=False)

            raw = await self._priority_analyzer.invoke(input_text)
            data = json.loads(raw)

            result.priority = data.get("priority", "medium")
            result.reason = data.get("reason", "")

            result.steps.append({
                "step": "priority",
                "priority": result.priority,
                "reason": result.reason,
                "message": f"优先级分析: {result.priority} — {result.reason}",
            })

        except Exception as e:
            logger.error("[Workflow] 优先级分析失败: %s", e)
            result.error = f"优先级分析失败: {str(e)}"
            result.steps.append({"step": "priority", "error": str(e)})

        return result

    async def _step_dispatch(self, result: WorkflowResult) -> WorkflowResult:
        """Step 3: 自动派单"""
        try:
            from app.core.database import async_session_factory

            async with async_session_factory() as db:
                agent = await dispatch_agent.dispatch(
                    ticket_type=result.ticket_type,
                    priority=result.priority,
                    db=db,
                )

            if agent is None:
                result.error = "当前无可用客服"
                result.steps.append({"step": "dispatch", "error": "无可用客服"})
                return result

            result.service_id = agent.id
            result.service_name = agent.name
            result.load_ratio = agent.load_ratio

            result.steps.append({
                "step": "dispatch",
                "service_id": agent.id,
                "service_name": agent.name,
                "skill_type": agent.skill_type,
                "load_ratio": agent.load_ratio,
                "message": f"派单成功: {agent.name} (负载率: {agent.load_ratio:.0%})",
            })

        except Exception as e:
            logger.error("[Workflow] 派单失败: %s", e)
            result.error = f"派单失败: {str(e)}"
            result.steps.append({"step": "dispatch", "error": str(e)})

        return result

    async def _step_notify(self, result: WorkflowResult) -> WorkflowResult:
        """Step 4: 通知客服（模拟）"""
        # TODO: 接入真实通知系统（WebSocket / 短信 / 邮件）
        result.steps.append({
            "step": "notify",
            "service_id": result.service_id,
            "message": f"已通知客服 {result.service_name}，等待处理",
        })

        logger.info("[Workflow] 已通知客服: %s (ID: %d)", result.service_name, result.service_id or 0)
        return result


# ---- 全局单例 ----

ticket_workflow = TicketWorkflow()
