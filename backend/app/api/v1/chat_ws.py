"""
Chat WebSocket API — 实时聊天接口。
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from pydantic import BaseModel, Field

from app.ai.services.chat_handler import chat_manager
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat WebSocket"])


# ============================================================
#  WebSocket: 用户端聊天
# ============================================================

@router.websocket("/ws/chat/user/{user_id}")
async def user_chat_websocket(websocket: WebSocket, user_id: int):
    """
    用户端聊天 WebSocket。
    """
    logger.info("[ChatWS] === 用户连接请求: user_id=%d ===", user_id)
    try:
        await chat_manager.user_online(user_id, websocket)
        logger.info("[ChatWS] 用户已上线: user_id=%d, ws_state=%d", user_id, websocket.client_state.value)
    except Exception as e:
        logger.error("[ChatWS] user_online 失败: %s", e)
        return

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            logger.info("[ChatWS] 收到: user_id=%d, type=%s", user_id, msg.get("type"))

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg.get("type") == "join_room":
                ticket_id = msg.get("ticket_id")
                if ticket_id:
                    await chat_manager.join_room(ticket_id, "user", user_id, websocket)

            elif msg.get("type") == "leave_room":
                ticket_id = msg.get("ticket_id")
                if ticket_id:
                    await chat_manager.leave_room(ticket_id, "user", user_id)

            elif msg.get("type") == "send_message":
                ticket_id = msg.get("ticket_id")
                content = msg.get("content", "")
                message_type = msg.get("message_type", "text")
                if ticket_id and content:
                    await chat_manager.send_message(
                        ticket_id=ticket_id,
                        sender_id=user_id,
                        sender_type="user",
                        content=content,
                        message_type=message_type,
                    )

            elif msg.get("type") == "mark_read":
                ticket_id = msg.get("ticket_id")
                if ticket_id:
                    await chat_manager.mark_read(ticket_id, "user", user_id)

    except WebSocketDisconnect:
        chat_manager.user_offline(user_id)
    except Exception as e:
        logger.error("[Chat WS] 用户连接异常: %s", e)
        chat_manager.user_offline(user_id)


# ============================================================
#  WebSocket: 客服端聊天
# ============================================================

@router.websocket("/ws/chat/service/{service_id}")
async def service_chat_websocket(websocket: WebSocket, service_id: int):
    """
    客服端聊天 WebSocket。

    功能:
    - 接收新工单弹窗提醒
    - 进入工单会话房间
    - 发送/接收消息
    - 已读状态
    - 在线状态
    """
    await chat_manager.service_online(service_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg.get("type") == "join_room":
                ticket_id = msg.get("ticket_id")
                if ticket_id:
                    await chat_manager.join_room(ticket_id, "service", service_id, websocket)

            elif msg.get("type") == "leave_room":
                ticket_id = msg.get("ticket_id")
                if ticket_id:
                    await chat_manager.leave_room(ticket_id, "service", service_id)

            elif msg.get("type") == "send_message":
                ticket_id = msg.get("ticket_id")
                content = msg.get("content", "")
                message_type = msg.get("message_type", "text")
                if ticket_id and content:
                    await chat_manager.send_message(
                        ticket_id=ticket_id,
                        sender_id=service_id,
                        sender_type="service",
                        content=content,
                        message_type=message_type,
                    )

            elif msg.get("type") == "mark_read":
                ticket_id = msg.get("ticket_id")
                if ticket_id:
                    await chat_manager.mark_read(ticket_id, "service", service_id)

            elif msg.get("type") == "accept_ticket":
                ticket_id = msg.get("ticket_id")
                if ticket_id:
                    from sqlalchemy import select
                    from app.models.ticket import Ticket
                    from app.core.database import async_session_factory
                    async with async_session_factory() as db:
                        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
                        ticket = result.scalar_one_or_none()
                        if ticket:
                            ticket.service_id = service_id
                            ticket.status = "processing"
                            await db.commit()

                            # 广播工单状态更新
                            room = chat_manager.get_room(ticket_id)
                            await room.broadcast({
                                "type": "ticket_status_changed",
                                "ticket_id": ticket_id,
                                "status": "processing",
                                "service_id": service_id,
                            })

    except WebSocketDisconnect:
        chat_manager.service_offline(service_id)
    except Exception as e:
        logger.error("[Chat WS] 客服连接异常: %s", e)
        chat_manager.service_offline(service_id)


# ============================================================
#  REST: 消息历史
# ============================================================

class MessageHistoryResponse(BaseModel):
    messages: list[dict]
    total: int


@router.get("/chat/messages/{ticket_id}")
async def get_messages(
    ticket_id: int,
    limit: int = Query(50, ge=1, le=200),
    before_id: int | None = None,
):
    """获取消息历史"""
    messages = await chat_manager.get_messages(ticket_id, limit, before_id)
    return {"messages": messages, "total": len(messages)}


# ============================================================
#  REST: 未读消息数
# ============================================================

@router.get("/chat/unread/{ticket_id}")
async def get_unread_count(
    ticket_id: int,
    reader_type: str = Query(..., description="user/service"),
):
    """获取未读消息数"""
    count = await chat_manager.get_unread_count(ticket_id, reader_type)
    return {"unread_count": count}


@router.get("/chat/unread-batch")
async def get_unread_count_batch(
    ticket_ids: str = Query(..., description="逗号分隔的工单ID列表"),
    reader_type: str = Query(..., description="user/service"),
):
    """批量获取多个工单的未读消息数"""
    ids = [int(x) for x in ticket_ids.split(",") if x.strip().isdigit()]
    result = {}
    for tid in ids:
        count = await chat_manager.get_unread_count(tid, reader_type)
        if count > 0:
            result[str(tid)] = count
    return {"unread_counts": result}


# ============================================================
#  REST: 在线状态
# ============================================================

@router.get("/chat/online")
async def online_status():
    """获取在线状态"""
    return chat_manager.get_stats()
