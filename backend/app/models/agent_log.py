"""
Agent 日志模型 — 存储 Agent 执行日志和工具调用日志。
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentExecutionLog(Base):
    """
    Agent 执行日志表。

    记录每次 Agent 工作流的执行信息。
    """
    __tablename__ = "agent_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, comment="追踪ID")
    user_id: Mapped[int] = mapped_column(Integer, index=True, comment="用户ID")
    conversation_id: Mapped[str] = mapped_column(String(100), index=True, comment="会话ID")

    # 输入信息
    user_input: Mapped[str] = mapped_column(Text, comment="用户输入")

    # 执行结果
    answer: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI回答")
    need_human: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否需要转人工")
    transfer_reason: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="转人工原因")

    # 工单信息
    ticket_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="工单类型")
    ticket_priority: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="工单优先级")
    ticket_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="工单ID")
    assignee_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="分配客服ID")

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="执行状态")

    # 性能指标
    total_duration_ms: Mapped[float] = mapped_column(Float, default=0.0, comment="总耗时(ms)")
    agent_count: Mapped[int] = mapped_column(Integer, default=0, comment="Agent调用次数")
    tool_count: Mapped[int] = mapped_column(Integer, default=0, comment="工具调用次数")

    # Agent 日志详情
    agent_logs: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="Agent执行日志")

    # 工具日志详情
    tool_logs: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="工具调用日志")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self) -> str:
        return f"<AgentExecutionLog trace_id={self.trace_id} status={self.status}>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "user_input": self.user_input,
            "answer": self.answer,
            "need_human": self.need_human,
            "transfer_reason": self.transfer_reason,
            "ticket_type": self.ticket_type,
            "ticket_priority": self.ticket_priority,
            "ticket_id": self.ticket_id,
            "assignee_id": self.assignee_id,
            "status": self.status,
            "total_duration_ms": self.total_duration_ms,
            "agent_count": self.agent_count,
            "tool_count": self.tool_count,
            "agent_logs": self.agent_logs,
            "tool_logs": self.tool_logs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentStatistics(Base):
    """
    Agent 统计表 — 存储按日期聚合的统计数据。
    """
    __tablename__ = "agent_statistics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stat_date: Mapped[str] = mapped_column(String(10), unique=True, index=True, comment="统计日期 YYYY-MM-DD")

    # Agent 调用次数
    knowledge_agent_count: Mapped[int] = mapped_column(Integer, default=0, comment="KnowledgeAgent调用次数")
    classification_agent_count: Mapped[int] = mapped_column(Integer, default=0, comment="ClassificationAgent调用次数")
    priority_agent_count: Mapped[int] = mapped_column(Integer, default=0, comment="PriorityAgent调用次数")
    ticket_creator_agent_count: Mapped[int] = mapped_column(Integer, default=0, comment="TicketCreatorAgent调用次数")
    dispatch_agent_count: Mapped[int] = mapped_column(Integer, default=0, comment="DispatchAgent调用次数")
    tool_calling_agent_count: Mapped[int] = mapped_column(Integer, default=0, comment="ToolCallingAgent调用次数")

    # Agent 调用次数
    total_agent_calls: Mapped[int] = mapped_column(Integer, default=0, comment="Agent总调用次数")
    successful_agent_calls: Mapped[int] = mapped_column(Integer, default=0, comment="Agent成功调用次数")
    failed_agent_calls: Mapped[int] = mapped_column(Integer, default=0, comment="Agent失败调用次数")

    # Agent 平均耗时 (ms)
    avg_agent_duration_ms: Mapped[float] = mapped_column(Float, default=0.0, comment="Agent平均耗时(ms)")

    # 工具调用次数
    query_ticket_count: Mapped[int] = mapped_column(Integer, default=0, comment="query_ticket调用次数")
    query_order_count: Mapped[int] = mapped_column(Integer, default=0, comment="query_order调用次数")
    query_refund_count: Mapped[int] = mapped_column(Integer, default=0, comment="query_refund调用次数")
    search_knowledge_count: Mapped[int] = mapped_column(Integer, default=0, comment="search_knowledge调用次数")
    search_web_count: Mapped[int] = mapped_column(Integer, default=0, comment="search_web调用次数")

    # 工具调用统计
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0, comment="工具总调用次数")
    successful_tool_calls: Mapped[int] = mapped_column(Integer, default=0, comment="工具成功调用次数")
    failed_tool_calls: Mapped[int] = mapped_column(Integer, default=0, comment="工具失败调用次数")

    # 工具平均耗时 (ms)
    avg_tool_duration_ms: Mapped[float] = mapped_column(Float, default=0.0, comment="工具平均耗时(ms)")

    # 总体统计
    total_conversations: Mapped[int] = mapped_column(Integer, default=0, comment="总咨询数量")
    ai_resolved_count: Mapped[int] = mapped_column(Integer, default=0, comment="AI解决数量（无需转人工）")
    transferred_count: Mapped[int] = mapped_column(Integer, default=0, comment="转人工数量")

    # 计算指标
    ai_resolution_rate: Mapped[float] = mapped_column(Float, default=0.0, comment="AI解决率")
    transfer_rate: Mapped[float] = mapped_column(Float, default=0.0, comment="转人工率")
    auto_dispatch_rate: Mapped[float] = mapped_column(Float, default=0.0, comment="工单自动派单率")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self) -> str:
        return f"<AgentStatistics date={self.stat_date}>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "stat_date": self.stat_date,
            "knowledge_agent_count": self.knowledge_agent_count,
            "classification_agent_count": self.classification_agent_count,
            "priority_agent_count": self.priority_agent_count,
            "ticket_creator_agent_count": self.ticket_creator_agent_count,
            "dispatch_agent_count": self.dispatch_agent_count,
            "tool_calling_agent_count": self.tool_calling_agent_count,
            "total_agent_calls": self.total_agent_calls,
            "successful_agent_calls": self.successful_agent_calls,
            "failed_agent_calls": self.failed_agent_calls,
            "avg_agent_duration_ms": self.avg_agent_duration_ms,
            "query_ticket_count": self.query_ticket_count,
            "query_order_count": self.query_order_count,
            "query_refund_count": self.query_refund_count,
            "search_knowledge_count": self.search_knowledge_count,
            "search_web_count": self.search_web_count,
            "total_tool_calls": self.total_tool_calls,
            "successful_tool_calls": self.successful_tool_calls,
            "failed_tool_calls": self.failed_tool_calls,
            "avg_tool_duration_ms": self.avg_tool_duration_ms,
            "total_conversations": self.total_conversations,
            "ai_resolved_count": self.ai_resolved_count,
            "transferred_count": self.transferred_count,
            "ai_resolution_rate": self.ai_resolution_rate,
            "transfer_rate": self.transfer_rate,
            "auto_dispatch_rate": self.auto_dispatch_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ToolExecutionLog(Base):
    """
    工具执行日志表。

    记录每次工具调用的详细信息。
    """
    __tablename__ = "tool_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(36), index=True, comment="追踪ID")

    # 工具信息
    tool_name: Mapped[str] = mapped_column(String(50), index=True, comment="工具名称")
    tool_input: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="工具输入参数")
    tool_output: Mapped[str | None] = mapped_column(Text, nullable=True, comment="工具输出结果")

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="执行状态")
    error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    # 性能指标
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, comment="耗时(ms)")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")

    def __repr__(self) -> str:
        return f"<ToolExecutionLog trace_id={self.trace_id} tool={self.tool_name}>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output[:200] if self.tool_output else None,
            "status": self.status,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }