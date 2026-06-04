"""
WebSocket API — 实时通知接口。
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.ai.services.websocket_manager import ws_manager
from app.ai.services.auto_flow import auto_flow
from app.core.database import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


# ============================================================
#  WebSocket: 客服端
# ============================================================

@router.websocket("/ws/service/{service_id}")
async def service_websocket(websocket: WebSocket, service_id: int):
    """
    客服端 WebSocket 连接。

    连接后自动接收:
    - 新工单通知
    - 工单状态更新
    - 派单结果
    """
    await ws_manager.connect_service(service_id, websocket)
    try:
        while True:
            # 接收客户端消息（心跳/操作）
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg.get("type") == "accept_ticket":
                # 客服接单
                ticket_id = msg.get("ticket_id")
                if ticket_id:
                    async with async_session_factory() as db:
                        from app.models.ticket import Ticket
                        from sqlalchemy import select
                        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
                        ticket = result.scalar_one_or_none()
                        if ticket:
                            ticket.service_id = service_id
                            ticket.status = "processing"
                            await db.commit()

                            # 广播工单状态更新
                            await ws_manager.broadcast_ticket_update({
                                "ticket_id": ticket_id,
                                "status": "processing",
                                "service_id": service_id,
                            })

            elif msg.get("type") == "resolve_ticket":
                # 客服解决工单
                ticket_id = msg.get("ticket_id")
                if ticket_id:
                    async with async_session_factory() as db:
                        from app.models.ticket import Ticket
                        from sqlalchemy import select
                        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
                        ticket = result.scalar_one_or_none()
                        if ticket:
                            ticket.status = "resolved"
                            await db.commit()

                            await ws_manager.broadcast_ticket_update({
                                "ticket_id": ticket_id,
                                "status": "resolved",
                            })

    except WebSocketDisconnect:
        ws_manager.disconnect_service(service_id)
    except Exception as e:
        logger.error("[WS] 客服连接异常: %s", e)
        ws_manager.disconnect_service(service_id)


# ============================================================
#  WebSocket: 用户端
# ============================================================

@router.websocket("/ws/user/{user_id}")
async def user_websocket(websocket: WebSocket, user_id: int):
    """
    用户端 WebSocket 连接。

    连接后自动接收:
    - 工单状态更新
    - 客服回复通知
    """
    await ws_manager.connect_user(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect_user(user_id)
    except Exception as e:
        logger.error("[WS] 用户连接异常: %s", e)
        ws_manager.disconnect_user(user_id)


# ============================================================
#  WebSocket: 自动流转（工单创建后自动触发）
# ============================================================

@router.websocket("/ws/auto-flow")
async def auto_flow_websocket(websocket: WebSocket):
    """
    自动流转 WebSocket。

    客户端发送工单数据，服务端自动执行:
    1. 分类
    2. 派单
    3. 通知客服
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "process_ticket":
                # 自动流转
                await websocket.send_json({
                    "type": "status",
                    "message": "开始处理...",
                })

                async with async_session_factory() as db:
                    result = await auto_flow.run(
                        title=msg.get("title", ""),
                        content=msg.get("content", ""),
                        user_id=msg.get("user_id"),
                        db=db,
                    )

                await websocket.send_json({
                    "type": "result",
                    "data": result,
                })

            elif msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("[WS] 自动流转连接断开")
    except Exception as e:
        logger.error("[WS] 自动流转异常: %s", e)


# ============================================================
#  REST: 获取 WebSocket 状态
# ============================================================

@router.get("/ws/stats")
async def ws_stats():
    """获取 WebSocket 连接统计"""
    return ws_manager.get_stats()
