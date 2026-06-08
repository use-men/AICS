"""
Agent State — 统一的 Agent 状态数据结构。

所有 Agent 通过 State 传递数据，实现解耦和可追溯。
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


@dataclass
class AgentLog:
    """Agent 执行日志"""
    agent_name: str                           # Agent 名称
    agent_type: AgentType | None = None       # Agent 类型
    start_time: datetime = field(default_factory=datetime.now)  # 开始时间
    end_time: datetime | None = None          # 结束时间
    duration_ms: float = 0.0                  # 耗时（毫秒）
    status: str = "pending"                   # 状态：pending/running/completed/failed
    input_summary: str = ""                   # 输入摘要
    output_summary: str = ""                  # 输出摘要
    error: str | None = None                  # 错误信息

    def start(self):
        """标记开始"""
        self.start_time = datetime.now()
        self.status = "running"

    def complete(self, output_summary: str = ""):
        """标记完成"""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = "completed"
        self.output_summary = output_summary

    def fail(self, error: str):
        """标记失败"""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = "failed"
        self.error = error

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type.value if self.agent_type else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "error": self.error,
        }


@dataclass
class ToolLog:
    """工具调用日志"""
    tool_name: str                           # 工具名称
    tool_input: dict = field(default_factory=dict)  # 工具输入参数
    tool_output: Any = None                  # 工具输出结果
    start_time: datetime = field(default_factory=datetime.now)  # 开始时间
    end_time: datetime | None = None          # 结束时间
    duration_ms: float = 0.0                  # 耗时（毫秒）
    status: str = "pending"                   # 状态：pending/running/completed/failed
    error: str | None = None                  # 错误信息

    def start(self):
        """标记开始"""
        self.start_time = datetime.now()
        self.status = "running"

    def complete(self, output: Any = None):
        """标记完成"""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = "completed"
        self.tool_output = output

    def fail(self, error: str):
        """标记失败"""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = "failed"
        self.error = error

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": str(self.tool_output)[:200] if self.tool_output else None,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "error": self.error,
        }

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type.value if self.agent_type else None,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "error": self.error,
        }


class AgentType(str, Enum):
    """Agent 类型枚举"""
    CUSTOMER_SERVICE = "cs_agent"           # AI 客服
    TICKET_CLASSIFIER = "ticket_classifier"  # 工单分类
    PRIORITY_ANALYZER = "priority_analyzer"  # 优先级分析
    TICKET_CREATOR = "ticket_creator"        # 工单创建
    DISPATCHER = "dispatcher"                # 智能派单
    KNOWLEDGE = "knowledge_agent"            # 知识库问答
    TOOL_CALLING = "tool_calling"            # Tool Calling
    SUPERVISOR = "supervisor"                # 统一调度


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"           # 待处理
    PROCESSING = "processing"     # 处理中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    TRANSFERRED = "transferred"   # 已转人工


class TransferReason(str, Enum):
    """转人工原因"""
    USER_REQUEST = "user_request"         # 用户主动要求
    LOW_CONFIDENCE = "low_confidence"     # 置信度低
    LLM_JUDGMENT = "llm_judgment"         # AI 判断需要转人工
    ERROR = "error"                       # 系统错误
    COMPLEX_ISSUE = "complex_issue"       # 复杂问题


@dataclass
class SearchResult:
    """知识库搜索结果"""
    question: str = ""
    answer: str = ""
    score: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class WebSearchResult:
    """联网搜索结果"""
    title: str = ""
    url: str = ""
    content: str = ""


@dataclass
class TicketInfo:
    """工单信息"""
    ticket_no: str = ""
    title: str = ""
    content: str = ""
    ticket_type: str = ""
    priority: str = ""
    status: str = ""
    user_id: int = 0
    assignee_id: int | None = None
    created_at: datetime | None = None


@dataclass
class AgentState:
    """
    统一的 Agent 状态数据结构。

    所有 Agent 通过这个状态对象传递数据，
    确保数据流的清晰和可追溯性。
    """

    # ---- 输入 ----
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 追踪 ID
    user_input: str = ""                    # 用户输入
    user_id: int = 0                        # 用户 ID
    conversation_id: str = "default"        # 会话 ID
    ticket_id: int | None = None            # 工单 ID（如果有）

    # ---- 知识库 ----
    knowledge_results: list[SearchResult] = field(default_factory=list)
    knowledge_context: str = ""             # 格式化后的知识库上下文

    # ---- 联网搜索 ----
    web_search_results: list[WebSearchResult] = field(default_factory=list)
    web_search_context: str = ""            # 格式化后的搜索上下文

    # ---- 对话历史 ----
    history: list[dict] = field(default_factory=list)  # [{"role": "user/assistant", "content": "..."}]

    # ---- AI 回答 ----
    answer: str = ""                        # AI 生成的回答
    thinking_content: str = ""              # 深度思考内容（如果有）

    # ---- 置信度 ----
    confidence_score: float = 0.0           # 知识库检索最高分
    low_confidence: bool = False            # 是否低置信度

    # ---- 转人工 ----
    need_human: bool = False                # 是否需要转人工
    transfer_reason: TransferReason | None = None  # 转人工原因

    # ---- 工单 ----
    ticket_info: TicketInfo | None = None   # 工单信息
    ticket_type: str = ""                   # 工单分类
    ticket_priority: str = ""               # 工单优先级
    assignee_id: int | None = None          # 分配的客服 ID

    # ---- 元数据 ----
    agent_type: AgentType | None = None     # 当前执行的 Agent 类型
    status: TaskStatus = TaskStatus.PENDING # 任务状态
    error: str | None = None                # 错误信息
    metadata: dict = field(default_factory=dict)  # 额外元数据
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳

    # ---- 流式输出 ----
    stream_chunks: list[str] = field(default_factory=list)  # 流式输出片段

    # ---- Agent 执行日志 ----
    current_agent: str = ""                 # 当前执行的 Agent 名称
    agent_logs: list[AgentLog] = field(default_factory=list)  # Agent 执行日志列表

    # ---- Tool Calling 日志 ----
    tool_logs: list[ToolLog] = field(default_factory=list)  # 工具调用日志列表

    def set_knowledge_results(self, results: list[dict]):
        """设置知识库搜索结果"""
        self.knowledge_results = [
            SearchResult(
                question=r.get("metadata", {}).get("question", ""),
                answer=r.get("metadata", {}).get("answer", ""),
                score=r.get("score", 0.0),
                metadata=r.get("metadata", {}),
            )
            for r in results
        ]
        # 格式化上下文
        parts = []
        for i, sr in enumerate(self.knowledge_results, 1):
            parts.append(f"[{i}] 问题: {sr.question}\n回答: {sr.answer}")
        self.knowledge_context = "\n\n".join(parts) if parts else "暂无相关知识库内容"
        # 更新置信度
        if self.knowledge_results:
            self.confidence_score = max(sr.score for sr in self.knowledge_results)
            self.low_confidence = self.confidence_score < 0.3

    def set_web_search_results(self, results: list[dict]):
        """设置联网搜索结果"""
        self.web_search_results = [
            WebSearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
            )
            for r in results
        ]
        # 格式化上下文
        parts = []
        for i, wr in enumerate(self.web_search_results, 1):
            parts.append(f"[Web {i}] {wr.title}\n链接: {wr.url}\n摘要: {wr.content}")
        self.web_search_context = "\n\n".join(parts) if parts else "暂无互联网搜索结果"

    def add_history(self, role: str, content: str):
        """添加对话历史"""
        self.history.append({"role": role, "content": content})
        # 保留最近 6 条
        if len(self.history) > 6:
            self.history = self.history[-6:]

    def start_agent(self, agent_name: str, agent_type: AgentType | None = None, input_summary: str = ""):
        """开始执行 Agent，记录日志"""
        self.current_agent = agent_name
        log = AgentLog(
            agent_name=agent_name,
            agent_type=agent_type,
            input_summary=input_summary[:200],
        )
        log.start()
        self.agent_logs.append(log)
        return log

    def complete_agent(self, output_summary: str = ""):
        """完成当前 Agent，更新日志"""
        if self.agent_logs:
            self.agent_logs[-1].complete(output_summary[:200])
        self.current_agent = ""

    def fail_agent(self, error: str):
        """当前 Agent 失败，更新日志"""
        if self.agent_logs:
            self.agent_logs[-1].fail(error)
        self.current_agent = ""

    def get_total_duration_ms(self) -> float:
        """获取总耗时（毫秒）"""
        return sum(log.duration_ms for log in self.agent_logs)

    def get_agent_summary(self) -> list[dict]:
        """获取所有 Agent 执行摘要"""
        return [log.to_dict() for log in self.agent_logs]

    # ---- Tool Calling 日志方法 ----

    def start_tool(self, tool_name: str, tool_input: dict | None = None):
        """开始调用工具，记录日志"""
        log = ToolLog(
            tool_name=tool_name,
            tool_input=tool_input or {},
        )
        log.start()
        self.tool_logs.append(log)
        return log

    def complete_tool(self, output: Any = None):
        """完成当前工具调用，更新日志"""
        if self.tool_logs:
            self.tool_logs[-1].complete(output)

    def fail_tool(self, error: str):
        """当前工具调用失败，更新日志"""
        if self.tool_logs:
            self.tool_logs[-1].fail(error)

    def get_tool_summary(self) -> list[dict]:
        """获取所有工具调用摘要"""
        return [log.to_dict() for log in self.tool_logs]

    def get_total_tool_duration_ms(self) -> float:
        """获取工具调用总耗时（毫秒）"""
        return sum(log.duration_ms for log in self.tool_logs)

    def to_dict(self) -> dict:
        """转换为字典（便于序列化）"""
        return {
            "trace_id": self.trace_id,
            "user_input": self.user_input,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "ticket_id": self.ticket_id,
            "knowledge_context": self.knowledge_context,
            "web_search_context": self.web_search_context,
            "answer": self.answer,
            "confidence_score": self.confidence_score,
            "low_confidence": self.low_confidence,
            "need_human": self.need_human,
            "transfer_reason": self.transfer_reason.value if self.transfer_reason else None,
            "ticket_type": self.ticket_type,
            "ticket_priority": self.ticket_priority,
            "assignee_id": self.assignee_id,
            "status": self.status.value,
            "error": self.error,
            "current_agent": self.current_agent,
            "agent_logs": self.get_agent_summary(),
            "tool_logs": self.get_tool_summary(),
            "total_duration_ms": round(self.get_total_duration_ms(), 2),
            "total_tool_duration_ms": round(self.get_total_tool_duration_ms(), 2),
        }