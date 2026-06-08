"""
query_ticket_tool — 工单查询工具。

查询工单状态、创建时间、处理客服等信息。
"""

import logging
from datetime import datetime

from app.ai.tools.base import BaseTool, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class QueryTicketTool(BaseTool):
    """工单查询工具"""

    @property
    def name(self) -> str:
        return "query_ticket"

    @property
    def description(self) -> str:
        return "查询工单信息，包括工单状态、创建时间、处理客服等"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="ticket_id",
                type="int",
                description="工单ID",
                required=True,
            ),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工单查询。

        Args:
            ticket_id: 工单ID

        Returns:
            ToolResult 包含工单信息
        """
        ticket_id = kwargs.get("ticket_id")
        if not ticket_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="缺少必填参数: ticket_id",
            )

        try:
            from app.core.database import async_session_factory
            from app.models.ticket import Ticket
            from app.models.user import User
            from sqlalchemy import select

            async with async_session_factory() as db:
                # 查询工单
                result = await db.execute(
                    select(Ticket).where(Ticket.id == ticket_id)
                )
                ticket = result.scalar_one_or_none()

                if not ticket:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"工单不存在: {ticket_id}",
                    )

                # 查询处理客服（使用 service_id）
                assignee_name = None
                if ticket.service_id:
                    user_result = await db.execute(
                        select(User).where(User.id == ticket.service_id)
                    )
                    user = user_result.scalar_one_or_none()
                    if user:
                        assignee_name = user.nickname or user.username

                # 构建返回数据
                data = {
                    "ticket_id": ticket.id,
                    "ticket_no": ticket.ticket_no,
                    "title": ticket.title,
                    "content": ticket.content,
                    "ticket_type": ticket.ticket_type,
                    "priority": ticket.priority,
                    "status": ticket.status,
                    "status_label": self._get_status_label(ticket.status),
                    "priority_label": self._get_priority_label(ticket.priority),
                    "type_label": self._get_type_label(ticket.ticket_type),
                    "user_id": ticket.user_id,
                    "assignee_id": ticket.service_id,
                    "assignee_name": assignee_name,
                    "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                    "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                }

                logger.info("[QueryTicket] 查询成功: %s", ticket.ticket_no)
                return ToolResult(status=ToolStatus.SUCCESS, data=data)

        except Exception as e:
            logger.error("[QueryTicket] 查询失败: %s", e)
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    @staticmethod
    def _get_status_label(status: str) -> str:
        """获取状态标签"""
        labels = {
            "pending": "待分配",
            "assigned": "已分配",
            "processing": "处理中",
            "resolved": "已解决",
            "closed": "已关闭",
        }
        return labels.get(status, status)

    @staticmethod
    def _get_priority_label(priority: str) -> str:
        """获取优先级标签"""
        labels = {
            "urgent": "紧急",
            "high": "高",
            "medium": "中",
            "low": "低",
        }
        return labels.get(priority, priority)

    @staticmethod
    def _get_type_label(ticket_type: str) -> str:
        """获取类型标签"""
        labels = {
            "after_sales": "售后咨询",
            "technical": "技术支持",
            "refund": "退款申请",
            "complaint": "投诉建议",
        }
        return labels.get(ticket_type, ticket_type)


# ---- 全局单例 ----

query_ticket_tool = QueryTicketTool()