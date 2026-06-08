"""
query_refund_tool — 退款查询工具。

查询退款状态、退款时间等信息。
"""

import logging

from app.ai.tools.base import BaseTool, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class QueryRefundTool(BaseTool):
    """退款查询工具"""

    @property
    def name(self) -> str:
        return "query_refund"

    @property
    def description(self) -> str:
        return "查询退款信息，包括退款状态、退款时间、退款金额等"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="order_no",
                type="str",
                description="订单号",
                required=True,
            ),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        """
        执行退款查询。

        Args:
            order_no: 订单号

        Returns:
            ToolResult 包含退款信息
        """
        order_no = kwargs.get("order_no")
        if not order_no:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="缺少必填参数: order_no",
            )

        try:
            # 这里需要根据实际的退款表结构来查询
            # 目前返回模拟数据，实际项目中需要连接退款数据库
            logger.info("[QueryRefund] 查询退款: %s", order_no)

            # 模拟查询结果（实际项目中替换为真实查询）
            # from app.core.database import async_session_factory
            # from app.models.refund import Refund
            # from sqlalchemy import select
            #
            # async with async_session_factory() as db:
            #     result = await db.execute(
            #         select(Refund).where(Refund.order_no == order_no)
            #     )
            #     refund = result.scalar_one_or_none()

            # 模拟数据
            data = {
                "order_no": order_no,
                "has_refund": True,
                "refund_status": "completed",
                "refund_status_label": "退款完成",
                "refund_amount": 99.00,
                "refund_reason": "用户主动申请退款",
                "refund_method": "原路退回",
                "created_at": "2026-06-06T11:00:00",
                "completed_at": "2026-06-06T11:30:00",
                "estimated_arrival": "1-3个工作日",
                "refund_no": "RF202606060001",
            }

            logger.info("[QueryRefund] 查询成功: %s", order_no)
            return ToolResult(status=ToolStatus.SUCCESS, data=data)

        except Exception as e:
            logger.error("[QueryRefund] 查询失败: %s", e)
            return ToolResult(status=ToolStatus.ERROR, error=str(e))


# ---- 全局单例 ----

query_refund_tool = QueryRefundTool()