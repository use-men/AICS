"""
Agent 监控 API — 提供 Agent 执行统计和监控数据。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.agent_log import AgentExecutionLog, AgentStatistics, ToolExecutionLog
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-monitor", tags=["Agent Monitor"])


# ============================================================
#  响应模型
# ============================================================


class AgentStatsResponse(BaseModel):
    """Agent 统计响应"""
    # Agent 调用次数
    knowledge_agent_count: int = 0
    classification_agent_count: int = 0
    priority_agent_count: int = 0
    ticket_creator_agent_count: int = 0
    dispatch_agent_count: int = 0
    tool_calling_agent_count: int = 0

    # Agent 调用统计
    total_agent_calls: int = 0
    successful_agent_calls: int = 0
    failed_agent_calls: int = 0

    # Agent 平均耗时
    avg_agent_duration_ms: float = 0.0

    # 工具调用次数
    query_ticket_count: int = 0
    query_order_count: int = 0
    query_refund_count: int = 0
    search_knowledge_count: int = 0
    search_web_count: int = 0

    # 工具调用统计
    total_tool_calls: int = 0
    successful_tool_calls: int = 0
    failed_tool_calls: int = 0

    # 工具平均耗时
    avg_tool_duration_ms: float = 0.0

    # 总体统计
    total_conversations: int = 0
    ai_resolved_count: int = 0
    transferred_count: int = 0

    # 计算指标
    ai_resolution_rate: float = 0.0
    transfer_rate: float = 0.0
    auto_dispatch_rate: float = 0.0


class AgentExecutionLogResponse(BaseModel):
    """Agent 执行日志响应"""
    id: int
    trace_id: str
    user_id: int
    user_input: str
    answer: Optional[str] = None
    need_human: bool = False
    ticket_type: Optional[str] = None
    ticket_priority: Optional[str] = None
    status: str
    total_duration_ms: float = 0.0
    agent_count: int = 0
    tool_count: int = 0
    agent_logs: Optional[list] = None
    tool_logs: Optional[list] = None
    created_at: Optional[str] = None


class DailyStatsResponse(BaseModel):
    """每日统计响应"""
    date: str
    stats: AgentStatsResponse


# ============================================================
#  API 端点
# ============================================================


@router.get("/stats", response_model=AgentStatsResponse)
async def get_agent_stats(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取 Agent 统计数据。

    Args:
        days: 统计天数（默认7天）

    Returns:
        AgentStatsResponse 统计数据
    """
    try:
        # 计算日期范围（使用本地时间，加8小时时区偏移）
        from datetime import timezone, timedelta
        local_tz = timezone(timedelta(hours=8))
        end_date = datetime.now(local_tz).date()
        start_date = end_date - timedelta(days=days - 1)
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()

        # 查询统计数据
        result = await db.execute(
            select(AgentStatistics).where(
                and_(
                    AgentStatistics.stat_date >= start_date_str,
                    AgentStatistics.stat_date <= end_date_str,
                )
            )
        )
        stats_list = result.scalars().all()

        # 聚合统计数据
        aggregated = AgentStatsResponse()

        for stat in stats_list:
            # Agent 调用次数
            aggregated.knowledge_agent_count += stat.knowledge_agent_count
            aggregated.classification_agent_count += stat.classification_agent_count
            aggregated.priority_agent_count += stat.priority_agent_count
            aggregated.ticket_creator_agent_count += stat.ticket_creator_agent_count
            aggregated.dispatch_agent_count += stat.dispatch_agent_count
            aggregated.tool_calling_agent_count += stat.tool_calling_agent_count

            # Agent 调用统计
            aggregated.total_agent_calls += stat.total_agent_calls
            aggregated.successful_agent_calls += stat.successful_agent_calls
            aggregated.failed_agent_calls += stat.failed_agent_calls

            # 工具调用次数
            aggregated.query_ticket_count += stat.query_ticket_count
            aggregated.query_order_count += stat.query_order_count
            aggregated.query_refund_count += stat.query_refund_count
            aggregated.search_knowledge_count += stat.search_knowledge_count
            aggregated.search_web_count += stat.search_web_count

            # 工具调用统计
            aggregated.total_tool_calls += stat.total_tool_calls
            aggregated.successful_tool_calls += stat.successful_tool_calls
            aggregated.failed_tool_calls += stat.failed_tool_calls

            # 总体统计
            aggregated.total_conversations += stat.total_conversations
            aggregated.ai_resolved_count += stat.ai_resolved_count
            aggregated.transferred_count += stat.transferred_count

        # 计算平均值
        if stats_list:
            aggregated.avg_agent_duration_ms = sum(s.avg_agent_duration_ms for s in stats_list) / len(stats_list)
            aggregated.avg_tool_duration_ms = sum(s.avg_tool_duration_ms for s in stats_list) / len(stats_list)

        # 计算比率
        if aggregated.total_conversations > 0:
            aggregated.ai_resolution_rate = round(
                aggregated.ai_resolved_count / aggregated.total_conversations * 100, 2
            )
            aggregated.transfer_rate = round(
                aggregated.transferred_count / aggregated.total_conversations * 100, 2
            )

        # 计算自动派单率
        if aggregated.transferred_count > 0:
            dispatched_count = aggregated.ticket_creator_agent_count  # 简化：以创建工单数作为派单数
            aggregated.auto_dispatch_rate = round(
                dispatched_count / aggregated.transferred_count * 100, 2
            )

        return aggregated

    except Exception as e:
        logger.error("[AgentMonitor] 获取统计数据失败: %s", e)
        raise


@router.get("/daily-stats", response_model=list[DailyStatsResponse])
async def get_daily_stats(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取每日统计数据。

    Args:
        days: 统计天数（默认7天）

    Returns:
        每日统计数据列表
    """
    try:
        # 计算日期范围（使用本地时间，加8小时时区偏移）
        from datetime import timezone, timedelta
        local_tz = timezone(timedelta(hours=8))
        end_date = datetime.now(local_tz).date()
        start_date = end_date - timedelta(days=days - 1)
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()

        # 查询统计数据
        result = await db.execute(
            select(AgentStatistics).where(
                and_(
                    AgentStatistics.stat_date >= start_date_str,
                    AgentStatistics.stat_date <= end_date_str,
                )
            ).order_by(AgentStatistics.stat_date)
        )
        stats_list = result.scalars().all()

        # 转换为响应格式
        daily_stats = []
        for stat in stats_list:
            daily_stats.append(DailyStatsResponse(
                date=stat.stat_date,
                stats=AgentStatsResponse(
                    knowledge_agent_count=stat.knowledge_agent_count,
                    classification_agent_count=stat.classification_agent_count,
                    priority_agent_count=stat.priority_agent_count,
                    ticket_creator_agent_count=stat.ticket_creator_agent_count,
                    dispatch_agent_count=stat.dispatch_agent_count,
                    tool_calling_agent_count=stat.tool_calling_agent_count,
                    total_agent_calls=stat.total_agent_calls,
                    successful_agent_calls=stat.successful_agent_calls,
                    failed_agent_calls=stat.failed_agent_calls,
                    avg_agent_duration_ms=stat.avg_agent_duration_ms,
                    query_ticket_count=stat.query_ticket_count,
                    query_order_count=stat.query_order_count,
                    query_refund_count=stat.query_refund_count,
                    search_knowledge_count=stat.search_knowledge_count,
                    search_web_count=stat.search_web_count,
                    total_tool_calls=stat.total_tool_calls,
                    successful_tool_calls=stat.successful_tool_calls,
                    failed_tool_calls=stat.failed_tool_calls,
                    avg_tool_duration_ms=stat.avg_tool_duration_ms,
                    total_conversations=stat.total_conversations,
                    ai_resolved_count=stat.ai_resolved_count,
                    transferred_count=stat.transferred_count,
                    ai_resolution_rate=stat.ai_resolution_rate,
                    transfer_rate=stat.transfer_rate,
                    auto_dispatch_rate=stat.auto_dispatch_rate,
                ),
            ))

        return daily_stats

    except Exception as e:
        logger.error("[AgentMonitor] 获取每日统计数据失败: %s", e)
        raise


@router.get("/execution-logs", response_model=list[AgentExecutionLogResponse])
async def get_execution_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取 Agent 执行日志列表。

    Args:
        page: 页码
        page_size: 每页数量
        status: 状态筛选

    Returns:
        执行日志列表
    """
    try:
        # 构建查询
        query = select(AgentExecutionLog)

        if status:
            query = query.where(AgentExecutionLog.status == status)

        # 排序和分页
        query = query.order_by(AgentExecutionLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        # 执行查询
        result = await db.execute(query)
        logs = result.scalars().all()

        # 转换为响应格式
        return [
            AgentExecutionLogResponse(
                id=log.id,
                trace_id=log.trace_id,
                user_id=log.user_id,
                user_input=log.user_input,
                answer=log.answer,
                need_human=log.need_human,
                ticket_type=log.ticket_type,
                ticket_priority=log.ticket_priority,
                status=log.status,
                total_duration_ms=log.total_duration_ms,
                agent_count=log.agent_count,
                tool_count=log.tool_count,
                agent_logs=log.agent_logs,
                tool_logs=log.tool_logs,
                created_at=log.created_at.isoformat() if log.created_at else None,
            )
            for log in logs
        ]

    except Exception as e:
        logger.error("[AgentMonitor] 获取执行日志失败: %s", e)
        raise


@router.get("/execution-logs/{trace_id}")
async def get_execution_log(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取单条执行日志详情（包含工具调用日志）。

    Args:
        trace_id: 追踪ID

    Returns:
        执行日志详情，包含 agent_logs 和 tool_logs
    """
    try:
        # 获取执行日志
        result = await db.execute(
            select(AgentExecutionLog).where(AgentExecutionLog.trace_id == trace_id)
        )
        log = result.scalar_one_or_none()

        if not log:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="执行日志不存在")

        # 获取工具调用日志
        tool_result = await db.execute(
            select(ToolExecutionLog).where(ToolExecutionLog.trace_id == trace_id)
        )
        tool_logs = tool_result.scalars().all()

        return {
            "id": log.id,
            "trace_id": log.trace_id,
            "user_id": log.user_id,
            "user_input": log.user_input,
            "answer": log.answer,
            "need_human": log.need_human,
            "ticket_type": log.ticket_type,
            "ticket_priority": log.ticket_priority,
            "ticket_id": log.ticket_id,
            "assignee_id": log.assignee_id,
            "status": log.status,
            "total_duration_ms": log.total_duration_ms,
            "agent_count": log.agent_count,
            "tool_count": len(tool_logs),
            "agent_logs": log.agent_logs or [],
            "tool_logs": [tl.to_dict() for tl in tool_logs],
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }

    except Exception as e:
        logger.error("[AgentMonitor] 获取执行日志详情失败: %s", e)
        raise


# ============================================================
#  工具调用日志 API
# ============================================================


class ToolExecutionLogResponse(BaseModel):
    """工具执行日志响应"""
    id: int
    trace_id: str
    tool_name: str
    tool_input: Optional[dict] = None
    tool_output: Optional[str] = None
    status: str
    error: Optional[str] = None
    duration_ms: float = 0.0
    created_at: Optional[str] = None


@router.get("/tool-logs", response_model=list[ToolExecutionLogResponse])
async def get_tool_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    tool_name: Optional[str] = Query(None, description="工具名称筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取工具调用日志列表。

    Args:
        page: 页码
        page_size: 每页数量
        tool_name: 工具名称筛选

    Returns:
        工具调用日志列表
    """
    try:
        query = select(ToolExecutionLog)

        if tool_name:
            query = query.where(ToolExecutionLog.tool_name == tool_name)

        query = query.order_by(ToolExecutionLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        logs = result.scalars().all()

        return [
            ToolExecutionLogResponse(
                id=log.id,
                trace_id=log.trace_id,
                tool_name=log.tool_name,
                tool_input=log.tool_input,
                tool_output=log.tool_output,
                status=log.status,
                error=log.error,
                duration_ms=log.duration_ms,
                created_at=log.created_at.isoformat() if log.created_at else None,
            )
            for log in logs
        ]

    except Exception as e:
        logger.error("[AgentMonitor] 获取工具日志失败: %s", e)
        raise


# ============================================================
#  保存日志的辅助函数
# ============================================================


async def save_execution_log(
    db: AsyncSession,
    state: Any,
) -> None:
    """
    保存 Agent 执行日志到数据库。

    Args:
        db: 数据库会话
        state: AgentState 对象
    """
    try:
        log = AgentExecutionLog(
            trace_id=state.trace_id,
            user_id=state.user_id,
            conversation_id=state.conversation_id,
            user_input=state.user_input,
            answer=state.answer,
            need_human=state.need_human,
            transfer_reason=state.transfer_reason.value if state.transfer_reason else None,
            ticket_type=state.ticket_type,
            ticket_priority=state.ticket_priority,
            ticket_id=state.ticket_id,
            assignee_id=state.assignee_id,
            status=state.status.value,
            total_duration_ms=state.get_total_duration_ms(),
            agent_count=len(state.agent_logs),
            tool_count=len(state.tool_logs),
            agent_logs=[log.to_dict() for log in state.agent_logs],
            tool_logs=[log.to_dict() for log in state.tool_logs],
        )

        db.add(log)
        await db.commit()

        logger.info("[AgentMonitor] 保存执行日志: %s", state.trace_id)

    except Exception as e:
        logger.error("[AgentMonitor] 保存执行日志失败: %s", e)
        await db.rollback()


async def update_daily_statistics(
    db: AsyncSession,
    state: Any,
) -> None:
    """
    更新每日统计数据。

    Args:
        db: 数据库会话
        state: AgentState 对象
    """
    try:
        # 获取今天的日期字符串
        stat_date = datetime.utcnow().date().isoformat()

        # 查询今天的统计记录
        result = await db.execute(
            select(AgentStatistics).where(AgentStatistics.stat_date == stat_date)
        )
        stat = result.scalar_one_or_none()

        if not stat:
            # 创建新的统计记录
            stat = AgentStatistics(stat_date=stat_date)
            db.add(stat)

        # 更新 Agent 调用次数
        for agent_log in state.agent_logs:
            agent_name = agent_log.agent_name
            if agent_name == "knowledge_agent":
                stat.knowledge_agent_count += 1
            elif agent_name == "ticket_classifier":
                stat.classification_agent_count += 1
            elif agent_name == "priority_analyzer":
                stat.priority_agent_count += 1
            elif agent_name == "ticket_creator":
                stat.ticket_creator_agent_count += 1
            elif agent_name == "dispatcher":
                stat.dispatch_agent_count += 1
            elif agent_name == "tool_calling":
                stat.tool_calling_agent_count += 1

            # 更新 Agent 调用统计
            stat.total_agent_calls += 1
            if agent_log.status == "completed":
                stat.successful_agent_calls += 1
            else:
                stat.failed_agent_calls += 1

        # 更新工具调用次数
        for tool_log in state.tool_logs:
            tool_name = tool_log.tool_name
            if tool_name == "query_ticket":
                stat.query_ticket_count += 1
            elif tool_name == "query_order":
                stat.query_order_count += 1
            elif tool_name == "query_refund":
                stat.query_refund_count += 1
            elif tool_name == "search_knowledge":
                stat.search_knowledge_count += 1
            elif tool_name == "search_web":
                stat.search_web_count += 1

            # 更新工具调用统计
            stat.total_tool_calls += 1
            if tool_log.status == "completed":
                stat.successful_tool_calls += 1
            else:
                stat.failed_tool_calls += 1

        # 更新总体统计
        stat.total_conversations += 1
        if not state.need_human:
            stat.ai_resolved_count += 1
        else:
            stat.transferred_count += 1

        # 重新计算平均值
        if stat.total_agent_calls > 0:
            stat.avg_agent_duration_ms = (
                stat.avg_agent_duration_ms * (stat.total_agent_calls - len(state.agent_logs))
                + sum(log.duration_ms for log in state.agent_logs)
            ) / stat.total_agent_calls

        if stat.total_tool_calls > 0:
            stat.avg_tool_duration_ms = (
                stat.avg_tool_duration_ms * (stat.total_tool_calls - len(state.tool_logs))
                + sum(log.duration_ms for log in state.tool_logs)
            ) / stat.total_tool_calls

        # 重新计算比率
        if stat.total_conversations > 0:
            stat.ai_resolution_rate = round(
                stat.ai_resolved_count / stat.total_conversations * 100, 2
            )
            stat.transfer_rate = round(
                stat.transferred_count / stat.total_conversations * 100, 2
            )

        if stat.transferred_count > 0:
            stat.auto_dispatch_rate = round(
                stat.ticket_creator_agent_count / stat.transferred_count * 100, 2
            )

        await db.commit()

        logger.info("[AgentMonitor] 更新每日统计数据: %s", stat_date)

    except Exception as e:
        logger.error("[AgentMonitor] 更新每日统计数据失败: %s", e)
        await db.rollback()