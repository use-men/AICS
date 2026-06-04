"""
MemoryManager — 对话记忆管理。

支持:
    - 短期记忆: 基于滑动窗口的对话历史
    - 长期记忆: 可扩展对接向量数据库
"""

import logging
from dataclasses import dataclass, field
from collections import defaultdict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.ai.config import ai_settings

logger = logging.getLogger(__name__)


@dataclass
class ConversationMemory:
    """单个会话的记忆"""
    conversation_id: str
    messages: list[BaseMessage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_user_message(self, content: str) -> None:
        self.messages.append(HumanMessage(content=content))
        self._trim()

    def add_ai_message(self, content: str) -> None:
        self.messages.append(AIMessage(content=content))
        self._trim()

    def get_history(self, max_messages: int | None = None) -> list[BaseMessage]:
        """获取对话历史"""
        limit = max_messages or ai_settings.MEMORY_WINDOW_SIZE
        return self.messages[-limit:]

    def clear(self) -> None:
        self.messages.clear()

    def _trim(self) -> None:
        """滑动窗口裁剪"""
        max_size = ai_settings.MEMORY_WINDOW_SIZE
        if len(self.messages) > max_size:
            self.messages = self.messages[-max_size:]


class MemoryManager:
    """
    全局记忆管理器。

    管理所有会话的短期记忆，按 conversation_id 隔离。
    """

    def __init__(self):
        self._conversations: dict[str, ConversationMemory] = {}

    def get_memory(self, conversation_id: str) -> ConversationMemory:
        """获取或创建会话记忆"""
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = ConversationMemory(
                conversation_id=conversation_id,
            )
            logger.info("[Memory] 创建新会话: %s", conversation_id)
        return self._conversations[conversation_id]

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        """添加一条消息到会话记忆"""
        memory = self.get_memory(conversation_id)
        if role == "user":
            memory.add_user_message(content)
        elif role == "assistant":
            memory.add_ai_message(content)

    def get_history(self, conversation_id: str) -> list[BaseMessage]:
        """获取会话历史"""
        memory = self.get_memory(conversation_id)
        return memory.get_history()

    def clear_conversation(self, conversation_id: str) -> None:
        """清除会话记忆"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.info("[Memory] 清除会话: %s", conversation_id)

    @property
    def active_conversations(self) -> int:
        """当前活跃会话数"""
        return len(self._conversations)


# ---- 全局单例 ----

memory_manager = MemoryManager()
