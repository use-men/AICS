"""
WebSocketManager — 实时通知管理器。

功能:
    1. 管理 WebSocket 连接
    2. 按用户/角色广播消息
    3. 工单状态实时推送
"""

import json
import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 用户连接: {user_id: WebSocket}
        self._user_connections: dict[int, WebSocket] = {}
        # 角色连接: {role: [WebSocket, ...]}
        self._role_connections: dict[str, list[WebSocket]] = {}
        # 客服连接: {service_id: WebSocket}
        self._service_connections: dict[int, WebSocket] = {}

    # ---- 连接管理 ----

    async def connect_user(self, user_id: int, websocket: WebSocket):
        """用户连接"""
        await websocket.accept()
        self._user_connections[user_id] = websocket
        logger.info("[WS] 用户连接: %d", user_id)

    async def connect_service(self, service_id: int, websocket: WebSocket):
        """客服连接"""
        await websocket.accept()
        self._service_connections[service_id] = websocket
        logger.info("[WS] 客服连接: %d", service_id)

    async def connect_role(self, role: str, websocket: WebSocket):
        """角色连接（如所有客服）"""
        await websocket.accept()
        if role not in self._role_connections:
            self._role_connections[role] = []
        self._role_connections[role].append(websocket)
        logger.info("[WS] 角色连接: %s (总数: %d)", role, len(self._role_connections[role]))

    def disconnect_user(self, user_id: int):
        """用户断开"""
        self._user_connections.pop(user_id, None)
        logger.info("[WS] 用户断开: %d", user_id)

    def disconnect_service(self, service_id: int):
        """客服断开"""
        self._service_connections.pop(service_id, None)
        logger.info("[WS] 客服断开: %d", service_id)

    def disconnect_role(self, role: str, websocket: WebSocket):
        """角色断开"""
        if role in self._role_connections:
            self._role_connections[role] = [
                ws for ws in self._role_connections[role] if ws != websocket
            ]

    # ---- 消息发送 ----

    async def send_to_user(self, user_id: int, message: dict[str, Any]):
        """发送给指定用户"""
        ws = self._user_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error("[WS] 发送失败 user=%d: %s", user_id, e)
                self.disconnect_user(user_id)

    async def send_to_service(self, service_id: int, message: dict[str, Any]):
        """发送给指定客服"""
        ws = self._service_connections.get(service_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error("[WS] 发送失败 service=%d: %s", service_id, e)
                self.disconnect_service(service_id)

    async def broadcast_to_role(self, role: str, message: dict[str, Any]):
        """广播给指定角色"""
        connections = self._role_connections.get(role, [])
        disconnected = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        # 清理断开的连接
        for ws in disconnected:
            self._role_connections[role] = [
                w for w in self._role_connections[role] if w != ws
            ]

    async def broadcast_ticket_update(self, ticket_data: dict[str, Any]):
        """广播工单更新"""
        message = {
            "type": "ticket_update",
            "data": ticket_data,
        }

        # 通知工单创建者
        user_id = ticket_data.get("user_id")
        if user_id:
            await self.send_to_user(user_id, message)

        # 通知分配的客服
        service_id = ticket_data.get("service_id")
        if service_id:
            await self.send_to_service(service_id, message)

        # 通知所有客服（工作台刷新）
        await self.broadcast_to_role("customer_service", message)

    async def broadcast_new_ticket(self, ticket_data: dict[str, Any]):
        """广播新工单"""
        message = {
            "type": "new_ticket",
            "data": ticket_data,
        }

        # 通知所有客服
        await self.broadcast_to_role("customer_service", message)

        # 通知工单创建者
        user_id = ticket_data.get("user_id")
        if user_id:
            await self.send_to_user(user_id, {
                "type": "ticket_created",
                "data": ticket_data,
            })

    async def broadcast_dispatch_result(self, dispatch_data: dict[str, Any]):
        """广播派单结果"""
        message = {
            "type": "dispatch_result",
            "data": dispatch_data,
        }

        # 通知被分配的客服
        service_id = dispatch_data.get("service_id")
        if service_id:
            await self.send_to_service(service_id, message)

        # 通知所有客服（工作台刷新）
        await self.broadcast_to_role("customer_service", message)

    # ---- 状态查询 ----

    @property
    def online_users(self) -> int:
        return len(self._user_connections)

    @property
    def online_services(self) -> int:
        return len(self._service_connections)

    def get_stats(self) -> dict:
        return {
            "online_users": self.online_users,
            "online_services": self.online_services,
            "role_connections": {k: len(v) for k, v in self._role_connections.items()},
        }


# ---- 全局单例 ----

ws_manager = ConnectionManager()
