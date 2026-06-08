"""
Conversation model — 对话会话管理。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Conversation(Base):
    """对话会话表 — 管理 AI/人工/协同模式"""
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True, comment="会话唯一标识")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="用户ID")
    ticket_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="关联工单ID")
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="ai", comment="会话模式: ai/hybrid/human")
    ai_status: Mapped[str] = mapped_column(String(20), nullable=False, default="online", comment="AI状态: online/offline")
    agent_status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline", comment="客服状态: online/offline/busy")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
