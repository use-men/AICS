"""
Agent API — AI Agent 相关接口。
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

from app.ai.manager import agent_manager
from app.ai.services.ticket import (
    ClassifyRequest,
    ClassifyResponse,
    ticket_service,
)
from app.ai.agents.supervisor import supervisor_agent
from app.ai.schemas import AgentState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["AI Agent"])


# ============================================================
#  POST /api/v1/agent/classify — 工单分类
# ============================================================


@router.post("/classify", response_model=ClassifyResponse)
async def classify_ticket(payload: ClassifyRequest) -> ClassifyResponse:
    """
    工单自动分类。

    根据标题和内容，自动识别工单类型：
    - after_sales: 售后咨询
    - technical: 技术支持
    - refund: 退款申请
    - complaint: 投诉建议
    """
    try:
        result = await ticket_service.classify(payload)
        return result
    except Exception as e:
        logger.error("[API] 工单分类失败: %s", e)
        raise HTTPException(status_code=500, detail=f"分类服务异常: {str(e)}")


# ============================================================
#  POST /api/v1/agent/priority — 优先级分析
# ============================================================


class PriorityRequest(BaseModel):
    """优先级分析请求"""
    title: str = Field(..., min_length=1, max_length=200, description="工单标题")
    content: str = Field(..., min_length=1, max_length=5000, description="工单内容")
    user_level: str = Field(default="normal", description="用户等级: vip/enterprise/normal/free")
    complaint_count: int = Field(default=0, ge=0, description="历史投诉次数")


class PriorityResponse(BaseModel):
    """优先级分析响应"""
    priority: str = Field(..., description="优先级: urgent/high/medium/low")
    reason: str = Field(..., description="判断原因")


def _register_priority_agent():
    """注册优先级分析 Agent"""
    from app.ai.agents.priority_analyzer import PriorityAnalyzerAgent
    agent_manager.register(PriorityAnalyzerAgent())


# 模块加载时注册
_register_priority_agent()


@router.post("/priority", response_model=PriorityResponse)
async def analyze_priority(payload: PriorityRequest) -> PriorityResponse:
    """
    工单优先级分析。

    根据内容、用户等级、投诉历史，判断优先级：
    - urgent: 紧急
    - high: 高
    - medium: 中
    - low: 低
    """
    try:
        input_text = json.dumps({
            "title": payload.title,
            "content": payload.content,
            "user_level": payload.user_level,
            "complaint_count": payload.complaint_count,
        }, ensure_ascii=False)

        raw = await agent_manager.invoke("priority_analyzer", input_text)
        result = json.loads(raw)

        return PriorityResponse(
            priority=result["priority"],
            reason=result["reason"],
        )
    except Exception as e:
        logger.error("[API] 优先级分析失败: %s", e)
        raise HTTPException(status_code=500, detail=f"分析服务异常: {str(e)}")


# ============================================================
#  POST /api/v1/agent/knowledge — 知识库问答
# ============================================================


class KnowledgeRequest(BaseModel):
    """知识库问答请求"""
    question: str = Field(..., min_length=1, max_length=1000, description="用户问题")
    conversation_id: str = Field(default="default", description="会话ID，用于多轮对话")
    top_k: int = Field(default=3, ge=1, le=10, description="检索文档数量")


class KnowledgeResponse(BaseModel):
    """知识库问答响应"""
    answer: str = Field(..., description="回答内容")
    sources: list[dict] = Field(default=[], description="引用来源")


class DocumentImportRequest(BaseModel):
    """文档导入请求"""
    texts: list[str] = Field(..., min_length=1, description="文档内容列表")
    metadatas: list[dict] | None = Field(default=None, description="元数据列表")
    chunk_size: int = Field(default=500, ge=100, le=2000, description="分块大小")


class DocumentImportResponse(BaseModel):
    """文档导入响应"""
    total_chunks: int = Field(..., description="导入的文档块数量")
    total_docs: int = Field(..., description="知识库当前总文档数")


class KnowledgeStatsResponse(BaseModel):
    """知识库统计响应"""
    total_documents: int = Field(..., description="文档总数")


def _register_knowledge_agent():
    """注册知识库 Agent"""
    from app.ai.agents.knowledge_agent import KnowledgeAgent
    agent_manager.register(KnowledgeAgent())


_register_knowledge_agent()


@router.post("/knowledge", response_model=KnowledgeResponse)
async def knowledge_qa(payload: KnowledgeRequest) -> KnowledgeResponse:
    """
    知识库问答（RAG）。

    基于 FAISS 向量检索 + DeepSeek 生成答案，支持多轮对话。
    """
    try:
        input_text = payload.question
        raw = await agent_manager.invoke(
            "knowledge_agent",
            input_text,
            conversation_id=payload.conversation_id,
            top_k=payload.top_k,
        )
        result = json.loads(raw)

        return KnowledgeResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
        )
    except Exception as e:
        logger.error("[API] 知识库问答失败: %s", e)
        raise HTTPException(status_code=500, detail=f"问答服务异常: {str(e)}")


@router.post("/knowledge/stream")
async def knowledge_qa_stream(payload: KnowledgeRequest):
    """知识库流式问答"""
    async def generate():
        async for chunk in agent_manager.stream(
            "knowledge_agent",
            payload.question,
            conversation_id=payload.conversation_id,
            top_k=payload.top_k,
        ):
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============================================================
#  POST /api/v1/agent/knowledge/documents — 文档导入
# ============================================================


@router.post("/knowledge/documents", response_model=DocumentImportResponse)
async def import_documents(payload: DocumentImportRequest) -> DocumentImportResponse:
    """
    导入文档到知识库。

    支持批量导入，自动分块和向量化。
    """
    try:
        from app.ai.services.vector_store import vector_store
        logger.info("[API] vector_store: %s, doc_count: %d", id(vector_store), vector_store.doc_count)

        total_chunks = vector_store.add_documents(
            texts=payload.texts,
            metadatas=payload.metadatas,
            chunk_size=payload.chunk_size,
        )

        return DocumentImportResponse(
            total_chunks=total_chunks,
            total_docs=vector_store.doc_count,
        )
    except Exception as e:
        logger.error("[API] 文档导入失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e) or repr(e)}")


@router.get("/knowledge/stats", response_model=KnowledgeStatsResponse)
async def knowledge_stats() -> KnowledgeStatsResponse:
    """获取知识库统计信息"""
    from app.ai.services.vector_store import vector_store
    return KnowledgeStatsResponse(total_documents=vector_store.doc_count)


@router.delete("/knowledge/documents")
async def clear_documents():
    """清空知识库"""
    try:
        from app.ai.services.vector_store import vector_store
        vector_store.clear()
        return {"message": "知识库已清空"}
    except Exception as e:
        logger.error("[API] 清空知识库失败: %s", e)
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")


# ============================================================
#  POST /api/v1/agent/dispatch — 智能客服调度
# ============================================================


class DispatchRequest(BaseModel):
    """调度请求"""
    ticket_type: str = Field(..., description="工单类型: after_sales/technical/refund/complaint")
    priority: str = Field(default="medium", description="优先级: urgent/high/medium/low")


class DispatchResponse(BaseModel):
    """调度响应"""
    service_id: int = Field(..., description="客服ID")
    service_name: str = Field(..., description="客服姓名")
    skill_type: str = Field(..., description="客服技能类型")
    load_ratio: float = Field(..., description="当前负载率")


@router.post("/dispatch", response_model=DispatchResponse)
async def dispatch_ticket(payload: DispatchRequest) -> DispatchResponse:
    """
    智能客服调度。

    根据工单类型、优先级、客服技能、负载情况，自动分配最合适的客服。
    """
    from app.ai.agents.dispatcher import dispatch_agent
    from app.core.database import async_session_factory

    try:
        async with async_session_factory() as db:
            agent = await dispatch_agent.dispatch(
                ticket_type=payload.ticket_type,
                priority=payload.priority,
                db=db,
            )

            if agent is None:
                raise HTTPException(status_code=404, detail="当前无可用客服，请稍后再试")

            return DispatchResponse(
                service_id=agent.id,
                service_name=agent.name,
                skill_type=agent.skill_type,
                load_ratio=agent.load_ratio,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[API] 客服调度失败: %s", e)
        raise HTTPException(status_code=500, detail=f"调度服务异常: {str(e)}")


# ============================================================
#  POST /api/v1/agent/cs — 用户端 AI 客服
# ============================================================


class CSRequest(BaseModel):
    """AI 客服请求"""
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    conversation_id: str = Field(default="default", description="会话ID")
    user_id: int | None = Field(default=None, description="用户ID")
    deep_thinking: bool = Field(default=False, description="是否开启深度思考模式")
    ticket_id: int | None = Field(default=None, description="当前工单ID（hybrid模式）")


class CSResponse(BaseModel):
    """AI 客服响应"""
    answer: str = Field(..., description="AI回答")
    need_human: bool = Field(..., description="是否需要转人工")
    ticket_id: int | None = Field(default=None, description="自动创建的工单ID")
    sources: list[dict] = Field(default=[], description="引用来源")


def _register_cs_agent():
    """注册用户端 AI 客服 Agent"""
    from app.ai.agents.customer_service import CustomerServiceAgent
    agent_manager.register(CustomerServiceAgent())


_register_cs_agent()


@router.post("/cs", response_model=CSResponse)
async def customer_service_chat(payload: CSRequest) -> CSResponse:
    """
    用户端 AI 客服对话。

    - 基于 Multi-Agent 架构
    - SupervisorAgent → SmartDeskGraph → ToolCallingAgent → KnowledgeAgent
    - 需要转人工时自动创建工单 + 派单
    - 支持多轮对话
    """
    try:
        # 构建 AgentState
        state = AgentState(
            user_input=payload.message,
            user_id=payload.user_id or 0,
            conversation_id=payload.conversation_id,
        )

        # 调用 SupervisorAgent（内部使用 SmartDeskGraph）
        state = await supervisor_agent.run(state)

        # 构建返回结果
        result = {
            "answer": state.answer,
            "need_human": state.need_human,
            "sources": [
                {
                    "question": sr.question,
                    "answer": sr.answer[:200],
                    "score": round(sr.score, 3),
                }
                for sr in state.knowledge_results
            ],
        }

        # 如果需要转人工，执行转人工流程
        ticket_id = None
        if state.need_human and not state.ticket_id:
            transfer = await _auto_transfer(
                content=payload.message,
                conversation_id=payload.conversation_id,
                user_id=payload.user_id,
            )
            if transfer:
                ticket_id = transfer.get("ticket_id")
                state.ticket_id = ticket_id
        else:
            ticket_id = state.ticket_id

        # 保存执行日志到数据库
        await _save_state_to_db(state)

        return CSResponse(
            answer=result["answer"],
            need_human=result["need_human"],
            ticket_id=ticket_id,
            sources=result.get("sources", []),
        )
    except Exception as e:
        logger.error("[API] AI客服对话失败: %s", e)
        raise HTTPException(status_code=500, detail=f"客服服务异常: {str(e)}")


@router.post("/cs/stream")
async def customer_service_stream(payload: CSRequest):
    """
    用户端 AI 客服流式对话（SSE）。

    返回格式:
    - type: status/sources/delta/done/error/transfer
    - content: 文本内容
    - sources: 引用来源（仅 done 时）
    - need_human: 是否需要转人工（仅 done 时）
    - transfer: 自动转人工结果（仅 need_human=true 且自动创建工单成功时）

    当 need_human=true 时，后端自动:
    1. 创建工单（TicketCreationAgent）
    2. 自动派单（DispatchService）
    3. WebSocket 通知客服
    """
    async def generate():
        try:
            # 构建 AgentState
            state = AgentState(
                user_input=payload.message,
                user_id=payload.user_id or 0,
                conversation_id=payload.conversation_id,
            )

            # Hybrid 模式：保存用户消息到 TicketMessage
            if payload.ticket_id:
                await _save_ai_message_to_ticket(
                    ticket_id=payload.ticket_id,
                    content=payload.message,
                    user_id=payload.user_id or 0,
                    sender_type="user",
                )

            # 发送开始状态
            yield f"data: {json.dumps({'type': 'status', 'content': '正在分析问题...'}, ensure_ascii=False)}\n\n"

            # 调用 SupervisorAgent（内部使用 SmartDeskGraph）
            state = await supervisor_agent.run(state)

            # 发送知识库搜索结果
            if state.knowledge_results:
                sources = [
                    {
                        "question": sr.question,
                        "answer": sr.answer[:200],
                        "score": round(sr.score, 3),
                    }
                    for sr in state.knowledge_results
                ]
                yield f"data: {json.dumps({'type': 'sources', 'content': f'找到 {len(sources)} 条相关知识', 'sources': sources}, ensure_ascii=False)}\n\n"

            # 发送工具调用信息
            if state.tool_logs:
                yield f"data: {json.dumps({'type': 'status', 'content': f'已调用 {len(state.tool_logs)} 个工具'}, ensure_ascii=False)}\n\n"

            # 如果需要转人工，执行转人工流程
            transfer_info = None
            logger.info("[API] need_human=%s, ticket_id=%s", state.need_human, state.ticket_id)

            # 如果 SmartDeskGraph 已经创建了工单（state.ticket_id 已设置）
            # 构建 transfer_info 并发送 transfer 事件
            if state.need_human and state.ticket_id:
                transfer_info = {
                    "ticket_id": state.ticket_id,
                    "ticket_no": f"TK{state.ticket_id:06d}",
                    "title": state.ticket_info.title if state.ticket_info else "",
                    "ticket_type": state.ticket_type,
                    "type_name": {
                        "after_sales": "售后咨询",
                        "technical": "技术支持",
                        "refund": "退款申请",
                        "complaint": "投诉建议",
                    }.get(state.ticket_type, "售后咨询"),
                    "priority": state.ticket_priority,
                    "service_id": state.assignee_id,
                    "service_name": state.metadata.get("assignee_name", ""),
                }
                yield f"data: {json.dumps({'type': 'transfer', **transfer_info}, ensure_ascii=False)}\n\n"
            # 如果 SmartDeskGraph 没有创建工单，需要手动创建
            elif state.need_human and not state.ticket_id:
                yield f"data: {json.dumps({'type': 'status', 'content': '正在创建工单...'}, ensure_ascii=False)}\n\n"

                transfer_info = await _auto_transfer(
                    content=payload.message,
                    conversation_id=payload.conversation_id,
                    user_id=payload.user_id,
                )
                if transfer_info:
                    state.ticket_id = transfer_info.get("ticket_id")
                    yield f"data: {json.dumps({'type': 'transfer', **transfer_info}, ensure_ascii=False)}\n\n"

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'content': state.answer, 'need_human': state.need_human, 'ticket_id': state.ticket_id, 'trace_id': state.trace_id}, ensure_ascii=False)}\n\n"

            # Hybrid 模式：保存 AI 回复到 TicketMessage（供客服查看）
            if payload.ticket_id and state.answer:
                await _save_ai_message_to_ticket(
                    ticket_id=payload.ticket_id,
                    content=state.answer,
                    user_id=payload.user_id or 0,
                )

            # 保存执行日志到数据库
            await _save_state_to_db(state)

        except Exception as e:
            logger.error("[API] 流式对话失败: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


async def _auto_transfer(
    content: str,
    conversation_id: str = "default",
    user_id: int | None = None,
) -> dict | None:
    """
    自动转人工：创建工单 → 派单 → WebSocket 通知。

    Returns:
        转人工结果字典，失败返回 None
    """
    from app.ai.agents.ticket_creator import ticket_creator
    from app.ai.services.dispatch_service import dispatch_service
    from app.ai.services.websocket_manager import ws_manager
    from app.core.database import async_session_factory

    try:
        # 1. 创建工单
        raw = await ticket_creator.invoke(
            content,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        ticket_result = json.loads(raw)
        ticket_id = ticket_result.get("ticket_id")

        if not ticket_id:
            logger.error("[AutoTransfer] 工单创建失败")
            return None

        ticket_type = ticket_result.get("ticket_type", "after_sales")
        type_name = {
            "after_sales": "售后咨询",
            "technical": "技术支持",
            "refund": "退款申请",
            "complaint": "投诉建议",
        }.get(ticket_type, "售后咨询")

        result = {
            "ticket_id": ticket_id,
            "ticket_no": f"TK{ticket_id:06d}",
            "title": ticket_result.get("title", ""),
            "ticket_type": ticket_type,
            "type_name": type_name,
            "priority": ticket_result.get("priority", "medium"),
            "service_id": None,
            "service_name": "",
        }

        # 2. 自动派单
        try:
            async with async_session_factory() as db:
                dispatch_result = await dispatch_service.auto_dispatch(
                    ticket_id=ticket_id,
                    ticket_type=ticket_type,
                    db=db,
                )

                if "error" not in dispatch_result:
                    result["service_id"] = dispatch_result["service_id"]
                    result["service_name"] = dispatch_result["service_name"]

                    # 3. WebSocket 通知
                    try:
                        await ws_manager.broadcast_new_ticket({
                            "ticket_id": ticket_id,
                            "ticket_type": ticket_type,
                            "type_name": type_name,
                            "title": result["title"],
                        })
                        await ws_manager.broadcast_dispatch_result({
                            "ticket_id": ticket_id,
                            "service_id": result["service_id"],
                            "service_name": result["service_name"],
                            "ticket_type": ticket_type,
                            "type_name": type_name,
                        })
                    except Exception as e:
                        logger.warning("[AutoTransfer] WebSocket 通知失败: %s", e)
                else:
                    logger.warning("[AutoTransfer] 派单失败: %s", dispatch_result.get("error"))
        except Exception as e:
            logger.error("[AutoTransfer] 派单异常: %s", e)

        logger.info(
            "[AutoTransfer] 完成: ticket=%d, service=%s",
            ticket_id, result.get("service_name", "无"),
        )
        return result

    except Exception as e:
        logger.error("[AutoTransfer] 自动转人工失败: %s", e)
        return None


async def _save_ai_message_to_ticket(
    ticket_id: int,
    content: str,
    user_id: int = 0,
    sender_type: str = "ai",
) -> dict | None:
    """
    Hybrid 模式：保存消息到 TicketMessage 表，并通过 WebSocket 广播。

    当用户在 hybrid 模式下提问时，用户消息和AI回答都会写入 ticket_messages，
    人工客服可以在聊天窗口中看到完整的对话内容。
    """
    try:
        from app.core.database import async_session_factory
        from app.models.ticket_message import TicketMessage

        async with async_session_factory() as db:
            msg = TicketMessage(
                ticket_id=ticket_id,
                sender_id=user_id,
                sender_type=sender_type,
                content=content,
                message_type="text",
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)

            message_data = {
                "type": "new_message",
                "message": {
                    "id": msg.id,
                    "ticket_id": msg.ticket_id,
                    "sender_id": msg.sender_id,
                    "sender_type": msg.sender_type,
                    "content": msg.content,
                    "message_type": msg.message_type,
                    "is_read": msg.is_read,
                    "created_at": str(msg.created_at) if msg.created_at else None,
                }
            }

            logger.info("[HybridMode] 消息已保存: ticket=%d, type=%s", ticket_id, sender_type)

        # 通过 WebSocket 广播到聊天房间
        try:
            from app.ai.services.chat_handler import chat_manager
            room = chat_manager.get_room(ticket_id)
            await room.broadcast(message_data)
            logger.info("[HybridMode] 消息已广播: ticket=%d", ticket_id)
        except Exception as e:
            logger.warning("[HybridMode] WebSocket 广播失败: %s", e)

        return message_data

    except Exception as e:
        logger.error("[HybridMode] 保存消息失败: %s", e)
        return None


async def _save_state_to_db(state: AgentState) -> None:
    """
    将 AgentState 保存到数据库（Multi-Agent 架构）。

    分离保存：
    - AgentExecutionLog: Agent 执行日志
    - ToolExecutionLog: 工具调用日志
    - AgentStatistics: 每日统计数据

    Args:
        state: AgentState 对象
    """
    try:
        from app.core.database import async_session_factory
        from app.models.agent_log import AgentExecutionLog, AgentStatistics, ToolExecutionLog
        from app.ai.schemas import AgentLog, ToolLog

        async with async_session_factory() as db:
            # 1. 保存 Agent 执行日志（只保存 AgentLog 对象）
            agent_logs_data = []
            for log in state.agent_logs:
                if isinstance(log, AgentLog):
                    agent_logs_data.append(log.to_dict())

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
                agent_count=len(agent_logs_data),
                tool_count=len(state.tool_logs),
                agent_logs=agent_logs_data,
                tool_logs=[],  # 工具日志单独存储
            )
            db.add(log)

            # 2. 保存工具调用日志到单独的表
            for tool_log in state.tool_logs:
                if isinstance(tool_log, ToolLog):
                    tool_log_record = ToolExecutionLog(
                        trace_id=state.trace_id,
                        tool_name=tool_log.tool_name,
                        tool_input=tool_log.tool_input,
                        tool_output=str(tool_log.tool_output)[:1000] if tool_log.tool_output else None,
                        status=tool_log.status,
                        error=tool_log.error,
                        duration_ms=tool_log.duration_ms,
                    )
                    db.add(tool_log_record)

            # 3. 更新每日统计
            from datetime import timezone, timedelta
            local_tz = timezone(timedelta(hours=8))
            stat_date = datetime.now(local_tz).date().isoformat()

            result = await db.execute(
                select(AgentStatistics).where(AgentStatistics.stat_date == stat_date)
            )
            stat = result.scalar_one_or_none()

            if not stat:
                stat = AgentStatistics(
                    stat_date=stat_date,
                    knowledge_agent_count=0,
                    classification_agent_count=0,
                    priority_agent_count=0,
                    ticket_creator_agent_count=0,
                    dispatch_agent_count=0,
                    tool_calling_agent_count=0,
                    total_agent_calls=0,
                    successful_agent_calls=0,
                    failed_agent_calls=0,
                    avg_agent_duration_ms=0.0,
                    query_ticket_count=0,
                    query_order_count=0,
                    query_refund_count=0,
                    search_knowledge_count=0,
                    search_web_count=0,
                    total_tool_calls=0,
                    successful_tool_calls=0,
                    failed_tool_calls=0,
                    avg_tool_duration_ms=0.0,
                    total_conversations=0,
                    ai_resolved_count=0,
                    transferred_count=0,
                    ai_resolution_rate=0.0,
                    transfer_rate=0.0,
                    auto_dispatch_rate=0.0,
                )
                db.add(stat)

            # 4. 更新 Agent 调用次数（只处理 AgentLog 对象）
            for agent_log in state.agent_logs:
                if not isinstance(agent_log, AgentLog):
                    continue

                agent_name = agent_log.agent_name
                if agent_name == "knowledge_agent":
                    stat.knowledge_agent_count = (stat.knowledge_agent_count or 0) + 1
                elif agent_name == "ticket_classifier":
                    stat.classification_agent_count = (stat.classification_agent_count or 0) + 1
                elif agent_name == "priority_analyzer":
                    stat.priority_agent_count = (stat.priority_agent_count or 0) + 1
                elif agent_name == "ticket_creator":
                    stat.ticket_creator_agent_count = (stat.ticket_creator_agent_count or 0) + 1
                elif agent_name == "dispatcher":
                    stat.dispatch_agent_count = (stat.dispatch_agent_count or 0) + 1
                elif agent_name == "tool_calling":
                    stat.tool_calling_agent_count = (stat.tool_calling_agent_count or 0) + 1

                stat.total_agent_calls = (stat.total_agent_calls or 0) + 1
                if agent_log.status == "completed":
                    stat.successful_agent_calls = (stat.successful_agent_calls or 0) + 1
                else:
                    stat.failed_agent_calls = (stat.failed_agent_calls or 0) + 1

            # 5. 更新工具调用次数（只处理 ToolLog 对象）
            for tool_log in state.tool_logs:
                if not isinstance(tool_log, ToolLog):
                    continue

                tool_name = tool_log.tool_name
                if tool_name == "query_ticket":
                    stat.query_ticket_count = (stat.query_ticket_count or 0) + 1
                elif tool_name == "query_order":
                    stat.query_order_count = (stat.query_order_count or 0) + 1
                elif tool_name == "query_refund":
                    stat.query_refund_count = (stat.query_refund_count or 0) + 1
                elif tool_name == "search_knowledge":
                    stat.search_knowledge_count = (stat.search_knowledge_count or 0) + 1
                elif tool_name == "search_web":
                    stat.search_web_count = (stat.search_web_count or 0) + 1

                stat.total_tool_calls = (stat.total_tool_calls or 0) + 1
                if tool_log.status == "completed":
                    stat.successful_tool_calls = (stat.successful_tool_calls or 0) + 1
                else:
                    stat.failed_tool_calls = (stat.failed_tool_calls or 0) + 1

            # 6. 更新总体统计
            stat.total_conversations = (stat.total_conversations or 0) + 1
            if not state.need_human:
                stat.ai_resolved_count = (stat.ai_resolved_count or 0) + 1
            else:
                stat.transferred_count = (stat.transferred_count or 0) + 1

            # 7. 重新计算比率
            if stat.total_conversations > 0:
                stat.ai_resolution_rate = round(
                    (stat.ai_resolved_count or 0) / stat.total_conversations * 100, 2
                )
                stat.transfer_rate = round(
                    (stat.transferred_count or 0) / stat.total_conversations * 100, 2
                )

            await db.commit()
            logger.info("[AgentMonitor] 保存 AgentState: %s | Agent: %d | Tool: %d",
                       state.trace_id, len(agent_logs_data), len(state.tool_logs))

    except Exception as e:
        logger.error("[AgentMonitor] 保存 AgentState 失败: %s", e)


# ============================================================
#  POST /api/v1/agent/cs-reply-suggest — 客服 AI 辅助回复
# ============================================================


class CSReplySuggestRequest(BaseModel):
    """AI 推荐回复请求"""
    ticket_id: int = Field(..., description="工单ID")


class CSReplySuggestResponse(BaseModel):
    """AI 推荐回复响应"""
    suggested_reply: str = Field(..., description="AI 推荐回复内容")
    sources: list[dict] = Field(default=[], description="参考来源")


@router.post("/cs-reply-suggest", response_model=CSReplySuggestResponse)
async def cs_reply_suggest(
    payload: CSReplySuggestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CSReplySuggestResponse:
    """
    客服 AI 辅助回复。

    根据工单内容 + 历史回复 + 知识库检索，生成推荐回复。
    客服可一键采纳或编辑后发送。
    """
    from sqlalchemy import select as sa_select
    from app.models.ticket import Ticket, TicketReply
    from app.ai.services.knowledge_service import knowledge_service

    # 1. 查询工单 + 回复
    result = await db.execute(sa_select(Ticket).where(Ticket.id == payload.ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    reply_result = await db.execute(
        sa_select(TicketReply)
        .where(TicketReply.ticket_id == payload.ticket_id)
        .order_by(TicketReply.created_at)
    )
    replies = reply_result.scalars().all()

    # 2. 构建对话上下文
    conversation = f"用户问题: {ticket.content}"
    if replies:
        conversation += "\n\n已有回复:"
        for r in replies:
            role_label = "客服" if r.role == "service" else "用户" if r.role == "user" else "管理员"
            conversation += f"\n{role_label}: {r.content}"

    # 3. 检索知识库
    search_results = await knowledge_service.search(ticket.content, top_k=3)
    context_parts = []
    sources = []
    for i, sr in enumerate(search_results, 1):
        meta = sr.get("metadata", {})
        question = meta.get("question", "")
        answer = meta.get("answer", "")
        context_parts.append(f"[{i}] 问题: {question}\n回答: {answer}")
        sources.append({
            "question": question,
            "answer": answer[:200],
            "score": round(sr.get("score", 0), 3),
        })
    knowledge_context = "\n\n".join(context_parts) if context_parts else "暂无相关知识库内容"

    # 4. 调用 DeepSeek 生成推荐回复
    from app.ai.config import ai_settings
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=ai_settings.DEEPSEEK_MODEL,
        openai_api_key=ai_settings.DEEPSEEK_API_KEY,
        openai_api_base=ai_settings.DEEPSEEK_BASE_URL,
        temperature=0.3,
        max_tokens=1024,
    )

    system_prompt = """你是 SmartDesk 客服辅助系统，帮助客服人员生成专业的回复建议。

## 规则
1. 回复要专业、友好、简洁
2. 优先基于【知识库内容】回答
3. 结合工单上下文和已有对话
4. 使用中文
5. 如果知识库无相关内容，基于你的专业知识给出合理建议

## 知识库参考
{knowledge}

## 工单对话
{conversation}"""

    prompt = system_prompt.format(
        knowledge=knowledge_context,
        conversation=conversation,
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "请根据以上工单信息，生成一条推荐回复。"},
    ]

    try:
        response = await llm.ainvoke(messages)
        suggested = response.content.strip()
    except Exception as e:
        logger.error("[CSReplySuggest] LLM 调用失败: %s", e)
        suggested = "抱歉，AI 辅助服务暂时不可用，请手动回复。"

    return CSReplySuggestResponse(
        suggested_reply=suggested,
        sources=sources,
    )


# ============================================================
#  POST /api/v1/agent/create-ticket — 自动创建工单
# ============================================================


class CreateTicketRequest(BaseModel):
    """创建工单请求"""
    content: str = Field(..., min_length=1, max_length=5000, description="用户问题描述")
    conversation_id: str = Field(default="default", description="会话ID")
    user_id: int | None = Field(default=None, description="用户ID")


class CreateTicketResponse(BaseModel):
    """创建工单响应"""
    ticket_id: int = Field(..., description="工单ID")
    title: str = Field(..., description="工单标题")
    ticket_type: str = Field(..., description="工单类型")
    priority: str = Field(..., description="优先级")
    description: str = Field(..., description="问题描述")


def _register_ticket_creator():
    """注册工单创建 Agent"""
    from app.ai.agents.ticket_creator import TicketCreationAgent
    agent_manager.register(TicketCreationAgent())


_register_ticket_creator()


@router.post("/create-ticket", response_model=CreateTicketResponse)
async def create_ticket(payload: CreateTicketRequest) -> CreateTicketResponse:
    """
    自动创建工单。

    AI 分析用户问题，自动生成工单标题、分类、优先级并保存到数据库。
    """
    try:
        raw = await agent_manager.invoke(
            "ticket_creator",
            payload.content,
            conversation_id=payload.conversation_id,
            user_id=payload.user_id,
        )
        result = json.loads(raw)

        if result.get("ticket_id") is None:
            raise HTTPException(status_code=500, detail="工单创建失败")

        return CreateTicketResponse(
            ticket_id=result["ticket_id"],
            title=result["title"],
            ticket_type=result["ticket_type"],
            priority=result["priority"],
            description=result["description"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[API] 创建工单失败: %s", e)
        raise HTTPException(status_code=500, detail=f"创建工单异常: {str(e)}")


# ============================================================
#  POST /api/v1/agent/workflow — 工单自动流转
# ============================================================


class WorkflowRequest(BaseModel):
    """工作流请求"""
    ticket_id: int = Field(..., description="工单ID")
    title: str = Field(..., min_length=1, max_length=200, description="工单标题")
    content: str = Field(..., min_length=1, max_length=5000, description="工单内容")
    user_id: int | None = Field(default=None, description="用户ID")
    user_level: str = Field(default="normal", description="用户等级: vip/enterprise/normal/free")
    complaint_count: int = Field(default=0, ge=0, description="历史投诉次数")


class WorkflowStepResponse(BaseModel):
    """工作流步骤响应"""
    step: str = Field(..., description="步骤名称")
    message: str = Field(default="", description="步骤说明")
    data: dict = Field(default={}, description="步骤数据")


class WorkflowResponse(BaseModel):
    """工作流响应"""
    ticket_id: int = Field(..., description="工单ID")
    status: str = Field(..., description="工单状态")
    ticket_type: str = Field(..., description="工单类型")
    type_name: str = Field(..., description="类型中文名")
    confidence: float = Field(..., description="分类置信度")
    priority: str = Field(..., description="优先级")
    reason: str = Field(..., description="优先级原因")
    service_id: int | None = Field(default=None, description="客服ID")
    service_name: str = Field(default="", description="客服姓名")
    load_ratio: float = Field(default=0.0, description="客服负载率")
    steps: list[WorkflowStepResponse] = Field(default=[], description="执行步骤")
    error: str | None = Field(default=None, description="错误信息")


@router.post("/workflow", response_model=WorkflowResponse)
async def run_ticket_workflow(payload: WorkflowRequest) -> WorkflowResponse:
    """
    工单自动流转。

    完整流程: 分类 → 优先级分析 → 自动派单 → 通知客服

    状态流转: pending → assigned → processing → resolved → closed
    """
    from app.ai.workflows.ticket_workflow import ticket_workflow

    try:
        result = await ticket_workflow.run(
            ticket_id=payload.ticket_id,
            title=payload.title,
            content=payload.content,
            user_id=payload.user_id,
            user_level=payload.user_level,
            complaint_count=payload.complaint_count,
        )

        return WorkflowResponse(
            ticket_id=result.ticket_id,
            status=result.status,
            ticket_type=result.ticket_type,
            type_name=result.type_name,
            confidence=result.confidence,
            priority=result.priority,
            reason=result.reason,
            service_id=result.service_id,
            service_name=result.service_name,
            load_ratio=result.load_ratio,
            steps=[WorkflowStepResponse(**s) for s in result.steps],
            error=result.error,
        )
    except Exception as e:
        logger.error("[API] 工作流执行失败: %s", e)
        raise HTTPException(status_code=500, detail=f"工作流异常: {str(e)}")


# ============================================================
#  POST /api/v1/agent/graph-workflow — LangGraph 多Agent协作
# ============================================================


class GraphWorkflowRequest(BaseModel):
    """LangGraph 工作流请求"""
    user_question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    conversation_id: str = Field(default="default", description="会话ID")
    user_id: int | None = Field(default=None, description="用户ID")
    user_level: str = Field(default="normal", description="用户等级")
    complaint_count: int = Field(default=0, ge=0, description="历史投诉次数")


class GraphWorkflowResponse(BaseModel):
    """LangGraph 工作流响应"""
    final_answer: str = Field(..., description="最终回答")
    need_human: bool = Field(..., description="是否需要转人工")
    ticket_id: int | None = Field(default=None, description="工单ID")
    ticket_type: str = Field(default="", description="工单类型")
    type_name: str = Field(default="", description="类型中文名")
    priority: str = Field(default="", description="优先级")
    service_name: str = Field(default="", description="分配客服")
    steps: list[dict] = Field(default=[], description="执行步骤")
    mermaid: str = Field(default="", description="Mermaid流程图")


@router.post("/graph-workflow", response_model=GraphWorkflowResponse)
async def run_graph_workflow(payload: GraphWorkflowRequest) -> GraphWorkflowResponse:
    """
    LangGraph 多Agent协作工作流。

    流程: Classification → Priority → Knowledge → Dispatch → Response

    节点说明:
    - ClassificationAgent: 工单分类
    - PriorityAgent: 优先级分析
    - KnowledgeAgent: 知识库检索
    - DispatchAgent: 智能派单
    - ResponseAgent: 生成最终回答
    """
    from app.ai.workflows.agent_graph import agent_graph_workflow

    try:
        result = await agent_graph_workflow.run(
            user_question=payload.user_question,
            conversation_id=payload.conversation_id,
            user_id=payload.user_id,
            user_level=payload.user_level,
            complaint_count=payload.complaint_count,
        )

        return GraphWorkflowResponse(
            final_answer=result.get("final_answer", ""),
            need_human=result.get("need_human", False),
            ticket_id=result.get("ticket_id"),
            ticket_type=result.get("ticket_type", ""),
            type_name=result.get("type_name", ""),
            priority=result.get("priority", ""),
            service_name=result.get("service_name", ""),
            steps=result.get("steps", []),
            mermaid=agent_graph_workflow.get_mermaid(),
        )
    except Exception as e:
        logger.error("[API] LangGraph 工作流失败: %s", e)
        raise HTTPException(status_code=500, detail=f"工作流异常: {str(e)}")
