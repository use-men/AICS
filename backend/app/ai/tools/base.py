"""
Tool 基类和工具注册机制。

所有 Agent 工具继承 BaseTool 并通过 @register_tool 装饰器注册。
"""

import logging
from typing import Any, Callable

from langchain_core.tools import tool as langchain_tool, BaseTool

logger = logging.getLogger(__name__)

# ---- 工具注册表 ----

_tool_registry: dict[str, BaseTool] = {}


def register_tool(name: str | None = None, description: str | None = None):
    """
    装饰器：将函数注册为 Agent 工具。

    使用方式:
        @register_tool("search_ticket", "搜索工单")
        def search_ticket(query: str) -> str:
            ...
    """

    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or f"执行 {tool_name}"

        @langchain_tool(name=tool_name, description=tool_desc)
        def wrapped_tool(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        _tool_registry[tool_name] = wrapped_tool
        logger.info("[Tool] 注册工具: %s", tool_name)
        return wrapped_tool

    return decorator


def get_tool(name: str) -> BaseTool | None:
    """按名称获取已注册的工具"""
    return _tool_registry.get(name)


def get_tools(names: list[str] | None = None) -> list[BaseTool]:
    """
    获取工具列表。

    Args:
        names: 指定工具名称列表，None 则返回所有
    """
    if names is None:
        return list(_tool_registry.values())
    return [_tool_registry[n] for n in names if n in _tool_registry]


def list_tools() -> list[str]:
    """列出所有已注册的工具名称"""
    return list(_tool_registry.keys())
