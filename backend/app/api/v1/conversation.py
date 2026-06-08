"""
Conversation API — 对话会话管理接口。
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.ticket_message import TicketMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation", tags=["对话管理"])


# ============================================================
#  Models
# ============================================================

class ConversationCreateRequest(BaseModel):
    """创建对话请求"""
    conversation_id: str = Field(..., description="会话唯一标识")
    user_id: int = Field(..., description="用户ID")


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    conversation_id: str
    user_id: int
    ticket_id: int | None
    mode: str
    ai_status: str
    agent_status: str


class ConversationModeUpdateRequest(BaseModel):
    """更新对话模式请求"""
    mode: str = Field(..., description="会话模式: ai/hybrid/human")
    ticket_id: int | None = Field(default=None, description="关联工单ID")


class SaveMessageRequest(BaseModel):
    """保存消息请求"""
    ticket_id: int = Field(..., description="工单ID")
    sender_type: str = Field(..., description="发送者类型: user/ai/agent")
    sender_id: int = Field(default=0, description="发送者ID")
    content: str = Field(..., description="消息内容")
    message_type: str = Field(default="text", description="消息类型: text/image/file")


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    ticket_id: int
    sender_id: int
    sender_type: str
    content: str
    message_type: str
    created_at: str


# ============================================================
#  API Endpoints
# ============================================================

@router.post("/create", response_model=ConversationResponse)
async def create_conversation(
    payload: ConversationCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """创建或获取对话会话"""
    # 检查是否已存在
    result = await db.execute(
        select(Conversation).where(Conversation.conversation_id == payload.conversation_id)
    )
    conv = result.scalar_one_or_none()

    if not conv:
        conv = Conversation(
            conversation_id=payload.conversation_id,
            user_id=payload.user_id,
            mode="ai",
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        logger.info("[Conversation] 创建新会话: %s", payload.conversation_id)

    return ConversationResponse(
        id=conv.id,
        conversation_id=conv.conversation_id,
        user_id=conv.user_id,
        ticket_id=conv.ticket_id,
        mode=conv.mode,
        ai_status=conv.ai_status,
        agent_status=conv.agent_status,
    )


@router.put("/{conversation_id}/mode", response_model=ConversationResponse)
async def update_conversation_mode(
    conversation_id: str,
    payload: ConversationModeUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """更新对话模式（ai → hybrid → human）"""
    result = await db.execute(
        select(Conversation).where(Conversation.conversation_id == conversation_id)
    )
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    conv.mode = payload.mode
    if payload.ticket_id:
        conv.ticket_id = payload.ticket_id
        conv.agent_status = "online"

    await db.commit()
    await db.refresh(conv)

    logger.info("[Conversation] 更新模式: %s → %s", conversation_id, payload.mode)

    return ConversationResponse(
        id=conv.id,
        conversation_id=conv.conversation_id,
        user_id=conv.user_id,
        ticket_id=conv.ticket_id,
        mode=conv.mode,
        ai_status=conv.ai_status,
        agent_status=conv.agent_status,
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """获取对话信息"""
    result = await db.execute(
        select(Conversation).where(Conversation.conversation_id == conversation_id)
    )
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    return ConversationResponse(
        id=conv.id,
        conversation_id=conv.conversation_id,
        user_id=conv.user_id,
        ticket_id=conv.ticket_id,
        mode=conv.mode,
        ai_status=conv.ai_status,
        agent_status=conv.agent_status,
    )


@router.post("/message", response_model=MessageResponse)
async def save_message(
    payload: SaveMessageRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """保存消息到统一 Message 表（支持 user/ai/agent 三种类型）"""
    msg = TicketMessage(
        ticket_id=payload.ticket_id,
        sender_id=payload.sender_id,
        sender_type=payload.sender_type,
        content=payload.content,
        message_type=payload.message_type,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    logger.info("[Conversation] 保存消息: ticket=%d, type=%s", payload.ticket_id, payload.sender_type)

    return MessageResponse(
        id=msg.id,
        ticket_id=msg.ticket_id,
        sender_id=msg.sender_id,
        sender_type=msg.sender_type,
        content=msg.content,
        message_type=msg.message_type,
        created_at=msg.created_at.isoformat() if msg.created_at else "",
    )


@router.get("/messages/{ticket_id}", response_model=list[MessageResponse])
async def get_messages(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    """获取工单的所有消息（包含 user/ai/agent）"""
    result = await db.execute(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at)
    )
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=msg.id,
            ticket_id=msg.ticket_id,
            sender_id=msg.sender_id,
            sender_type=msg.sender_type,
            content=msg.content,
            message_type=msg.message_type,
            created_at=msg.created_at.isoformat() if msg.created_at else "",
        )
        for msg in messages
    ]
