"""
ChatService — AI 对话服务（对外接口层）。

封装 Agent 调用，提供面向 API 的对话接口。
"""

import logging
from typing import Any, AsyncIterator

from app.ai.manager import agent_manager
from app.ai.memory.manager import memory_manager

logger = logging.getLogger(__name__)


class ChatService:
    """
    AI 对话服务。

    使用方式:
        service = ChatService()
        result = await service.chat("qa_agent", "什么是工单？", conversation_id="conv_123")
    """

    async def chat(
        self,
        agent_name: str,
        message: str,
        conversation_id: str = "default",
        user_id: int | None = None,
    ) -> str:
        """
        发送消息并获取 Agent 响应。

        Args:
            agent_name: Agent 名称
            message: 用户消息
            conversation_id: 会话 ID
            user_id: 用户 ID

        Returns:
            Agent 响应文本
        """
        # 1. 获取对话历史
        history = memory_manager.get_history(conversation_id)

        # 2. 调用 Agent
        result = await agent_manager.invoke(
            agent_name,
            message,
            history=history,
            conversation_id=conversation_id,
            user_id=user_id,
        )

        # 3. 保存到记忆
        memory_manager.add_message(conversation_id, "user", message)
        memory_manager.add_message(conversation_id, "assistant", result)

        return result

    async def chat_stream(
        self,
        agent_name: str,
        message: str,
        conversation_id: str = "default",
        user_id: int | None = None,
    ) -> AsyncIterator[str]:
        """
        流式对话。

        Args:
            agent_name: Agent 名称
            message: 用户消息
            conversation_id: 会话 ID
            user_id: 用户 ID

        Yields:
            文本片段
        """
        history = memory_manager.get_history(conversation_id)

        full_response = ""
        async for chunk in agent_manager.stream(
            agent_name,
            message,
            history=history,
            conversation_id=conversation_id,
            user_id=user_id,
        ):
            full_response += chunk
            yield chunk

        # 保存完整响应到记忆
        memory_manager.add_message(conversation_id, "user", message)
        memory_manager.add_message(conversation_id, "assistant", full_response)

    def clear_conversation(self, conversation_id: str) -> None:
        """清除对话记忆"""
        memory_manager.clear_conversation(conversation_id)


# ---- 全局单例 ----

chat_service = ChatService()
