"""
TicketMessage model — 工单消息。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TicketMessage(Base):
    """工单消息表"""
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="发送者ID")
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="发送者类型: user/service/admin/ai")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    message_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text", comment="消息类型: text/image/file")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="已读状态")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 关联工单
    ticket: Mapped["Ticket"] = relationship(back_populates="messages")
