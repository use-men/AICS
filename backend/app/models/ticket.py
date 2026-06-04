"""
Ticket model — 工单系统。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from app.models.ticket_message import TicketMessage  # noqa: E402


class Ticket(Base):
    """工单表"""
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True, comment="工单编号")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="工单标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="工单内容")
    ticket_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="工单类型")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", comment="优先级")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True, comment="状态")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="用户ID")
    service_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="客服ID")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联回复
    replies: Mapped[list["TicketReply"]] = relationship(back_populates="ticket", lazy="selectin")
    messages: Mapped[list["TicketMessage"]] = relationship(back_populates="ticket", lazy="selectin")


class TicketReply(Base):
    """工单回复表"""
    __tablename__ = "ticket_replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="回复者ID")
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="角色: user/service/admin")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="回复内容")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped["Ticket"] = relationship(back_populates="replies")
