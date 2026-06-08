"""
Tool 基类和工具注册机制。

所有 Agent 工具继承 BaseTool 并通过 ToolRegistry 注册。
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
#  工具参数定义
# ============================================================


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str                          # 参数名
    type: str                          # 参数类型（str, int, float, bool）
    description: str = ""              # 参数描述
    required: bool = True              # 是否必填
    default: Any = None                # 默认值

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "default": self.default,
        }


# ============================================================
#  工具执行结果
# ============================================================


class ToolStatus(str, Enum):
    """工具执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """工具执行结果"""
    status: ToolStatus                 # 执行状态
    data: Any = None                   # 返回数据
    error: str | None = None           # 错误信息
    execution_time_ms: float = 0.0     # 执行耗时（毫秒）
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "timestamp": self.timestamp.isoformat(),
        }

    def is_success(self) -> bool:
        """是否执行成功"""
        return self.status == ToolStatus.SUCCESS


# ============================================================
#  BaseTool 基类
# ============================================================


class BaseTool(ABC):
    """
    工具基类。

    所有工具必须继承此基类并实现 execute 方法。

    使用方式:
        class MyTool(BaseTool):
            @property
            def name(self) -> str:
                return "my_tool"

            @property
            def description(self) -> str:
                return "我的工具描述"

            @property
            def parameters(self) -> list[ToolParameter]:
                return [
                    ToolParameter(name="query", type="str", description="查询内容"),
                ]

            async def execute(self, **kwargs) -> ToolResult:
                # 实现逻辑
                return ToolResult(status=ToolStatus.SUCCESS, data="结果")
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        ...

    @property
    @abstractmethod
    def parameters(self) -> list[ToolParameter]:
        """工具参数定义"""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        执行工具。

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult 执行结果
        """
        ...

    async def __call__(self, **kwargs: Any) -> ToolResult:
        """支持直接调用"""
        return await self.execute(**kwargs)

    def get_schema(self) -> dict:
        """获取工具的 JSON Schema（用于 LLM Function Calling）"""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"


# ============================================================
#  ToolRegistry 工具注册中心
# ============================================================


class ToolRegistry:
    """
    工具注册中心。

    支持：
        - register(): 注册工具
        - get(): 获取工具
        - execute(): 执行工具
        - list_tools(): 列出所有工具
        - get_schemas(): 获取所有工具的 Schema

    使用方式:
        registry = ToolRegistry()
        registry.register(MyTool())
        result = await registry.execute("my_tool", query="test")
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        name = tool.name
        if name in self._tools:
            logger.warning("[ToolRegistry] 覆盖注册: %s", name)
        self._tools[name] = tool
        logger.info("[ToolRegistry] 注册工具: %s (%s)", name, tool.__class__.__name__)

    def unregister(self, name: str) -> None:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            logger.info("[ToolRegistry] 注销工具: %s", name)
        else:
            logger.warning("[ToolRegistry] 注销失败，工具不存在: %s", name)

    def get(self, name: str) -> BaseTool | None:
        """获取工具"""
        return self._tools.get(name)

    def get_or_raise(self, name: str) -> BaseTool:
        """获取工具，不存在则抛出异常"""
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"工具不存在: {name}")
        return tool

    @property
    def tool_names(self) -> list[str]:
        """所有已注册的工具名称"""
        return list(self._tools.keys())

    @property
    def tool_count(self) -> int:
        """工具数量"""
        return len(self._tools)

    async def execute(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """
        执行工具。

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            ToolResult 执行结果
        """
        tool = self.get_or_raise(tool_name)
        logger.info("[ToolRegistry] 执行工具: %s | params: %s", tool_name, kwargs)

        start_time = datetime.now()
        try:
            result = await tool.execute(**kwargs)
            result.execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.info("[ToolRegistry] 工具执行完成: %s | status: %s | time: %.2fms",
                       tool_name, result.status.value, result.execution_time_ms)
            return result
        except Exception as e:
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.error("[ToolRegistry] 工具执行失败: %s | error: %s", tool_name, e)
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

    def get_schemas(self, tool_names: list[str] | None = None) -> list[dict]:
        """
        获取工具的 JSON Schema 列表。

        Args:
            tool_names: 指定工具名称列表，None 则返回所有

        Returns:
            工具 Schema 列表
        """
        if tool_names is None:
            return [tool.get_schema() for tool in self._tools.values()]
        return [self._tools[name].get_schema() for name in tool_names if name in self._tools]

    def list_tools(self) -> list[dict]:
        """列出所有工具信息"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": [p.to_dict() for p in tool.parameters],
            }
            for tool in self._tools.values()
        ]


# ============================================================
#  全局工具注册中心
# ============================================================


tool_registry = ToolRegistry()
