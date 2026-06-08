"""
query_order_tool — 订单查询工具。

查询订单状态、支付状态等信息。
"""

import logging

from app.ai.tools.base import BaseTool, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class QueryOrderTool(BaseTool):
    """订单查询工具"""

    @property
    def name(self) -> str:
        return "query_order"

    @property
    def description(self) -> str:
        return "查询订单信息，包括订单状态、支付状态、订单金额等"

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
        执行订单查询。

        Args:
            order_no: 订单号

        Returns:
            ToolResult 包含订单信息
        """
        order_no = kwargs.get("order_no")
        if not order_no:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="缺少必填参数: order_no",
            )

        try:
            # 这里需要根据实际的订单表结构来查询
            # 目前返回模拟数据，实际项目中需要连接订单数据库
            logger.info("[QueryOrder] 查询订单: %s", order_no)

            # 模拟查询结果（实际项目中替换为真实查询）
            # from app.core.database import async_session_factory
            # from app.models.order import Order
            # from sqlalchemy import select
            #
            # async with async_session_factory() as db:
            #     result = await db.execute(
            #         select(Order).where(Order.order_no == order_no)
            #     )
            #     order = result.scalar_one_or_none()

            # 模拟数据
            data = {
                "order_no": order_no,
                "status": "paid",
                "status_label": "已支付",
                "payment_status": "paid",
                "payment_status_label": "已支付",
                "payment_method": "alipay",
                "payment_method_label": "支付宝",
                "total_amount": 99.00,
                "paid_amount": 99.00,
                "currency": "CNY",
                "created_at": "2026-06-06T10:00:00",
                "paid_at": "2026-06-06T10:01:00",
                "items": [
                    {
                        "product_name": "SmartDesk Pro",
                        "quantity": 1,
                        "price": 99.00,
                    }
                ],
            }

            logger.info("[QueryOrder] 查询成功: %s", order_no)
            return ToolResult(status=ToolStatus.SUCCESS, data=data)

        except Exception as e:
            logger.error("[QueryOrder] 查询失败: %s", e)
            return ToolResult(status=ToolStatus.ERROR, error=str(e))


# ---- 全局单例 ----

query_order_tool = QueryOrderTool()