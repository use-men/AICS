"""
ChatHandler — WebSocket 实时聊天处理。

功能:
    1. 房间管理（用户+客服进入同一工单会话）
    2. 消息收发
    3. 在线状态
    4. 未读消息 / 已读状态
    5. 客服端新工单弹窗提醒
"""

import json
import logging
from typing import Any
from datetime import datetime

from fastapi import WebSocket
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket_message import TicketMessage
from app.models.ticket import Ticket
from app.core.database import async_session_factory

logger = logging.getLogger(__name__)


class ChatRoom:
    """单个聊天房间"""

    def __init__(self, ticket_id: int):
        self.ticket_id = ticket_id
        self.connections: dict[str, WebSocket] = {}  # {f"{sender_type}_{sender_id}": WebSocket}

    def add_connection(self, key: str, ws: WebSocket):
        self.connections[key] = ws

    def remove_connection(self, key: str):
        self.connections.pop(key, None)

    async def broadcast(self, message: dict, exclude: str | None = None):
        """广播消息到房间内所有连接"""
        for key, ws in self.connections.items():
            if key != exclude:
                try:
                    await ws.send_json(message)
                except Exception:
                    self.connections.pop(key, None)

    @property
    def online_count(self) -> int:
        return len(self.connections)


class ChatManager:
    """聊天管理器"""

    def __init__(self):
        self._rooms: dict[int, ChatRoom] = {}  # {ticket_id: ChatRoom}
        self._online_users: dict[int, WebSocket] = {}  # {user_id: WebSocket}
        self._online_services: dict[int, WebSocket] = {}  # {service_id: WebSocket}

    # ---- 房间管理 ----

    def get_room(self, ticket_id: int) -> ChatRoom:
        """获取或创建聊天房间"""
        if ticket_id not in self._rooms:
            self._rooms[ticket_id] = ChatRoom(ticket_id)
        return self._rooms[ticket_id]

    # ---- 用户/客服在线管理 ----

    async def user_online(self, user_id: int, ws: WebSocket):
        """用户上线"""
        await ws.accept()
        self._online_users[user_id] = ws
        logger.info("[Chat] 用户上线: %d", user_id)

    async def service_online(self, service_id: int, ws: WebSocket):
        """客服上线"""
        await ws.accept()
        self._online_services[service_id] = ws
        logger.info("[Chat] 客服上线: %d", service_id)

    def user_offline(self, user_id: int):
        """用户下线"""
        self._online_users.pop(user_id, None)
        logger.info("[Chat] 用户下线: %d", user_id)

    def service_offline(self, service_id: int):
        """客服下线"""
        self._online_services.pop(service_id, None)
        logger.info("[Chat] 客服下线: %d", service_id)

    # ---- 进入房间 ----

    async def join_room(self, ticket_id: int, sender_type: str, sender_id: int, ws: WebSocket):
        """进入聊天房间"""
        # 注意: WebSocket 已在 user_online/service_online 中 accept，此处不再重复 accept
        room = self.get_room(ticket_id)
        key = f"{sender_type}_{sender_id}"
        room.add_connection(key, ws)

        # 通知房间内其他人
        await room.broadcast({
            "type": "user_joined",
            "sender_type": sender_type,
            "sender_id": sender_id,
            "online_count": room.online_count,
        }, exclude=key)

        # 也通知加入者本人当前在线人数
        try:
            await ws.send_json({
                "type": "user_joined",
                "sender_type": sender_type,
                "sender_id": sender_id,
                "online_count": room.online_count,
            })
        except Exception:
            pass

        logger.info("[Chat] 进入房间: ticket=%d, user=%s_%d, online=%d",
                     ticket_id, sender_type, sender_id, room.online_count)

    async def leave_room(self, ticket_id: int, sender_type: str, sender_id: int):
        """离开聊天房间"""
        room = self.get_room(ticket_id)
        key = f"{sender_type}_{sender_id}"
        room.remove_connection(key)

        await room.broadcast({
            "type": "user_left",
            "sender_type": sender_type,
            "sender_id": sender_id,
            "online_count": room.online_count,
        })

        logger.info("[Chat] 离开房间: ticket=%d, user=%s_%d", ticket_id, sender_type, sender_id)

    # ---- 发送消息 ----

    async def send_message(
        self,
        ticket_id: int,
        sender_id: int,
        sender_type: str,
        content: str,
        message_type: str = "text",
    ) -> dict | None:
        """
        发送消息。

        Returns:
            消息数据
        """
        # 1. 保存到数据库
        async with async_session_factory() as db:
            msg = TicketMessage(
                ticket_id=ticket_id,
                sender_id=sender_id,
                sender_type=sender_type,
                content=content,
                message_type=message_type,
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)

            message_data = {
                "type": "new_message",
                "message": {
                    "id": msg.id,
                    "ticket_id": msg.ticket_id,
                    "sender_id": msg.sender_id,
                    "sender_type": msg.sender_type,
                    "content": msg.content,
                    "message_type": msg.message_type,
                    "is_read": msg.is_read,
                    "created_at": str(msg.created_at) if msg.created_at else None,
                }
            }

        # 2. 广播到房间
        room = self.get_room(ticket_id)
        await room.broadcast(message_data)

        # 3. 通知不在线的用户/客服（推送未读）
        await self._notify_offline(ticket_id, sender_type, message_data)

        logger.info("[Chat] 消息发送: ticket=%d, sender=%s_%d, type=%s",
                    ticket_id, sender_type, sender_id, message_type)

        return message_data

    async def _notify_offline(self, ticket_id: int, sender_type: str, message_data: dict):
        """通知不在线的用户/客服"""
        async with async_session_factory() as db:
            result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
            ticket = result.scalar_one_or_none()
            if not ticket:
                return

            # 如果发送者是用户，通知客服
            if sender_type == "user" and ticket.service_id:
                ws = self._online_services.get(ticket.service_id)
                if ws:
                    try:
                        await ws.send_json({
                            "type": "new_ticket_message",
                            "ticket_id": ticket_id,
                            "sender_type": sender_type,
                        })
                    except Exception:
                        pass

            # 如果发送者是客服，通知用户
            if sender_type == "service":
                ws = self._online_users.get(ticket.user_id)
                if ws:
                    try:
                        await ws.send_json({
                            "type": "new_ticket_message",
                            "ticket_id": ticket_id,
                            "sender_type": sender_type,
                        })
                    except Exception:
                        pass

    # ---- 已读状态 ----

    async def mark_read(self, ticket_id: int, reader_type: str, reader_id: int):
        """标记消息已读"""
        async with async_session_factory() as db:
            await db.execute(
                update(TicketMessage)
                .where(
                    TicketMessage.ticket_id == ticket_id,
                    TicketMessage.sender_type != reader_type,
                    TicketMessage.is_read == False,
                )
                .values(is_read=True)
            )
            await db.commit()

        # 通知发送者消息已读
        room = self.get_room(ticket_id)
        await room.broadcast({
            "type": "messages_read",
            "ticket_id": ticket_id,
            "reader_type": reader_type,
            "reader_id": reader_id,
        })

    # ---- 获取消息历史 ----

    async def get_messages(
        self,
        ticket_id: int,
        limit: int = 50,
        before_id: int | None = None,
    ) -> list[dict]:
        """获取消息历史"""
        async with async_session_factory() as db:
            query = select(TicketMessage).where(TicketMessage.ticket_id == ticket_id)

            if before_id:
                query = query.where(TicketMessage.id < before_id)

            query = query.order_by(TicketMessage.created_at.desc()).limit(limit)
            result = await db.execute(query)
            messages = result.scalars().all()

            return [
                {
                    "id": msg.id,
                    "ticket_id": msg.ticket_id,
                    "sender_id": msg.sender_id,
                    "sender_type": msg.sender_type,
                    "content": msg.content,
                    "message_type": msg.message_type,
                    "is_read": msg.is_read,
                    "created_at": str(msg.created_at) if msg.created_at else None,
                }
                for msg in reversed(messages)
            ]

    # ---- 未读消息数 ----

    async def get_unread_count(self, ticket_id: int, reader_type: str) -> int:
        """获取未读消息数"""
        async with async_session_factory() as db:
            result = await db.execute(
                select(func.count(TicketMessage.id)).where(
                    TicketMessage.ticket_id == ticket_id,
                    TicketMessage.sender_type != reader_type,
                    TicketMessage.is_read == False,
                )
            )
            return result.scalar() or 0

    # ---- 新工单提醒（客服端弹窗） ----

    async def notify_new_ticket(self, ticket_data: dict):
        """通知所有客服有新工单"""
        message = {
            "type": "new_ticket_alert",
            "data": ticket_data,
        }
        for service_id, ws in self._online_services.items():
            try:
                await ws.send_json(message)
            except Exception:
                self._online_services.pop(service_id, None)

    # ---- 在线状态查询 ----

    def is_user_online(self, user_id: int) -> bool:
        return user_id in self._online_users

    def is_service_online(self, service_id: int) -> bool:
        return service_id in self._online_services

    def get_stats(self) -> dict:
        return {
            "online_users": len(self._online_users),
            "online_services": len(self._online_services),
            "active_rooms": len(self._rooms),
        }


# ---- 全局单例 ----

chat_manager = ChatManager()
