"""
AutoFlowAgent — 工单自动流转。

流程:
    用户提交问题
    ↓
    ClassificationAgent → 工单分类
    ↓
    DispatchAgent → 自动派单
    ↓
    WebSocket → 通知客服
    ↓
    客服工作台实时刷新
"""

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.ticket_classifier import TicketClassificationAgent
from app.ai.services.dispatch_service import dispatch_service
from app.ai.services.websocket_manager import ws_manager
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)

TICKET_TYPE_NAMES = {
    "after_sales": "售后咨询",
    "technical": "技术支持",
    "refund": "退款申请",
    "complaint": "投诉建议",
}


class AutoFlowAgent:
    """
    工单自动流转 Agent。

    编排: 分类 → 派单 → 通知
    """

    def __init__(self):
        self._classifier = TicketClassificationAgent()

    async def run(
        self,
        title: str,
        content: str,
        user_id: int | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        执行自动流转。

        Args:
            title: 工单标题
            content: 工单内容
            user_id: 用户ID
            db: 数据库会话

        Returns:
            流转结果
        """
        result = {
            "ticket_id": None,
            "ticket_type": "",
            "type_name": "",
            "confidence": 0.0,
            "service_id": None,
            "service_name": "",
            "status": "pending",
            "steps": [],
        }

        # Step 1: 分类
        try:
            classify_input = json.dumps({"title": title, "content": content}, ensure_ascii=False)
            classify_raw = await self._classifier.invoke(classify_input)
            classify_result = json.loads(classify_raw)

            result["ticket_type"] = classify_result.get("ticket_type", "after_sales")
            result["type_name"] = TICKET_TYPE_NAMES.get(result["ticket_type"], "售后咨询")
            result["confidence"] = classify_result.get("confidence", 0.5)

            result["steps"].append({
                "step": "classify",
                "status": "done",
                "message": f"分类: {result['type_name']} (置信度: {result['confidence']})",
            })

            logger.info("[AutoFlow] 分类完成: %s", result["ticket_type"])

        except Exception as e:
            logger.error("[AutoFlow] 分类失败: %s", e)
            result["steps"].append({"step": "classify", "status": "error", "message": str(e)})
            result["ticket_type"] = "after_sales"
            result["type_name"] = "售后咨询"

        # Step 2: 创建工单
        if db:
            try:
                ticket = Ticket(
                    ticket_no="",
                    title=title,
                    content=content,
                    ticket_type=result["ticket_type"],
                    priority="medium",
                    status="pending",
                    user_id=user_id or 0,
                )
                db.add(ticket)
                await db.flush()
                ticket.ticket_no = f"TK{ticket.id:06d}"
                await db.commit()

                result["ticket_id"] = ticket.id
                result["steps"].append({
                    "step": "create_ticket",
                    "status": "done",
                    "message": f"工单已创建: {ticket.ticket_no}",
                })

                logger.info("[AutoFlow] 工单已创建: %s", ticket.ticket_no)

            except Exception as e:
                logger.error("[AutoFlow] 创建工单失败: %s", e)
                result["steps"].append({"step": "create_ticket", "status": "error", "message": str(e)})

        # Step 3: 自动派单
        if db and result["ticket_id"]:
            try:
                dispatch_result = await dispatch_service.auto_dispatch(
                    ticket_id=result["ticket_id"],
                    ticket_type=result["ticket_type"],
                    db=db,
                )

                if "error" not in dispatch_result:
                    result["service_id"] = dispatch_result["service_id"]
                    result["service_name"] = dispatch_result["service_name"]
                    result["status"] = "assigned"

                    result["steps"].append({
                        "step": "dispatch",
                        "status": "done",
                        "message": f"已分配给: {result['service_name']}",
                    })

                    logger.info("[AutoFlow] 派单完成: %s", result["service_name"])

                    # Step 4: WebSocket 通知
                    await self._notify(result)
                else:
                    result["steps"].append({
                        "step": "dispatch",
                        "status": "warning",
                        "message": dispatch_result["error"],
                    })

            except Exception as e:
                logger.error("[AutoFlow] 派单失败: %s", e)
                result["steps"].append({"step": "dispatch", "status": "error", "message": str(e)})

        return result

    async def _notify(self, result: dict[str, Any]):
        """WebSocket 通知"""
        try:
            # 通知客服有新工单
            await ws_manager.broadcast_new_ticket({
                "ticket_id": result["ticket_id"],
                "ticket_type": result["ticket_type"],
                "type_name": result["type_name"],
                "title": f"新工单: {result['type_name']}",
            })

            # 通知被分配的客服
            if result["service_id"]:
                await ws_manager.broadcast_dispatch_result({
                    "ticket_id": result["ticket_id"],
                    "service_id": result["service_id"],
                    "service_name": result["service_name"],
                    "ticket_type": result["ticket_type"],
                    "type_name": result["type_name"],
                })

        except Exception as e:
            logger.error("[AutoFlow] 通知失败: %s", e)

    async def process_ticket(
        self,
        ticket_id: int,
        title: str,
        content: str,
        ticket_type: str,
        user_id: int | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        处理已创建的工单（分类 + 派单 + 通知）。

        Args:
            ticket_id: 工单ID
            title: 工单标题
            content: 工单内容
            ticket_type: 工单类型（可选，如已分类）
            user_id: 用户ID
            db: 数据库会话

        Returns:
            处理结果
        """
        result = {
            "ticket_id": ticket_id,
            "ticket_type": ticket_type,
            "type_name": TICKET_TYPE_NAMES.get(ticket_type, "售后咨询"),
            "service_id": None,
            "service_name": "",
            "status": "pending",
            "steps": [],
        }

        # 派单
        if db:
            try:
                dispatch_result = await dispatch_service.auto_dispatch(
                    ticket_id=ticket_id,
                    ticket_type=ticket_type,
                    db=db,
                )

                if "error" not in dispatch_result:
                    result["service_id"] = dispatch_result["service_id"]
                    result["service_name"] = dispatch_result["service_name"]
                    result["status"] = "assigned"

                    result["steps"].append({
                        "step": "dispatch",
                        "status": "done",
                        "message": f"已分配给: {result['service_name']}",
                    })

                    # 通知
                    await self._notify(result)
                else:
                    result["steps"].append({
                        "step": "dispatch",
                        "status": "warning",
                        "message": dispatch_result["error"],
                    })

            except Exception as e:
                logger.error("[AutoFlow] 派单失败: %s", e)
                result["steps"].append({"step": "dispatch", "status": "error", "message": str(e)})

        return result


# ---- 全局单例 ----

auto_flow = AutoFlowAgent()
