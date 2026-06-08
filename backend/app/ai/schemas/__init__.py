"""
Agent Schemas — 统一的数据结构定义。
"""

from app.ai.schemas.state import (
    AgentState,
    AgentLog,
    AgentType,
    TaskStatus,
    TransferReason,
    SearchResult,
    WebSearchResult,
    TicketInfo,
    ToolLog,
)

__all__ = [
    "AgentState",
    "AgentLog",
    "AgentType",
    "TaskStatus",
    "TransferReason",
    "SearchResult",
    "WebSearchResult",
    "TicketInfo",
    "ToolLog",
]