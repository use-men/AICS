"""
Agent 工具集 — 每个工具是一个可被 Agent 调用的函数。
"""

from app.ai.tools.base import BaseTool, ToolParameter, ToolResult, ToolStatus, ToolRegistry, tool_registry
from app.ai.tools.web_search import web_search, format_web_results
from app.ai.tools.query_ticket import QueryTicketTool, query_ticket_tool
from app.ai.tools.query_order import QueryOrderTool, query_order_tool
from app.ai.tools.query_refund import QueryRefundTool, query_refund_tool
from app.ai.tools.search_knowledge import SearchKnowledgeTool, search_knowledge_tool
from app.ai.tools.search_web import SearchWebTool, search_web_tool

__all__ = [
    # 基类
    "BaseTool",
    "ToolParameter",
    "ToolResult",
    "ToolStatus",
    "ToolRegistry",
    "tool_registry",
    # 旧工具（兼容）
    "web_search",
    "format_web_results",
    # 新工具
    "QueryTicketTool",
    "query_ticket_tool",
    "QueryOrderTool",
    "query_order_tool",
    "QueryRefundTool",
    "query_refund_tool",
    "SearchKnowledgeTool",
    "search_knowledge_tool",
    "SearchWebTool",
    "search_web_tool",
]


def register_default_tools():
    """注册所有默认工具到 tool_registry"""
    tool_registry.register(query_ticket_tool)
    tool_registry.register(query_order_tool)
    tool_registry.register(query_refund_tool)
    tool_registry.register(search_knowledge_tool)
    tool_registry.register(search_web_tool)


# 自动注册默认工具
register_default_tools()
