"""
Workflow 基类 — 基于 LangGraph 的工作流抽象。

后续具体业务 Agent 的工作流将继承此基类。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict, total=False):
    """工作流状态基类"""
    input: str
    output: str
    error: str | None
    metadata: dict[str, Any]


class BaseWorkflow(ABC):
    """
    LangGraph 工作流基类。

    子类实现:
        - workflow_name: 工作流名称
        - build_graph(): 构建状态图
    """

    @property
    @abstractmethod
    def workflow_name(self) -> str:
        ...

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """构建并返回 LangGraph StateGraph"""
        ...

    def compile(self):
        """编译工作流为可执行图"""
        graph = self.build_graph()
        compiled = graph.compile()
        logger.info("[Workflow] 编译完成: %s", self.workflow_name)
        return compiled

    async def run(self, input_text: str, **kwargs: Any) -> dict[str, Any]:
        """执行工作流"""
        app = self.compile()
        initial_state: WorkflowState = {
            "input": input_text,
            "output": "",
            "error": None,
            "metadata": kwargs,
        }
        result = await app.ainvoke(initial_state)
        return result
