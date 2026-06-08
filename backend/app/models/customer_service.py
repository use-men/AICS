"""
CustomerService model — 客服人员信息。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class CustomerService(Base):
    """客服人员表"""
    __tablename__ = "customer_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, unique=True, index=True, comment="关联用户ID")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="客服姓名")
    skill_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="技能类型: after_sales/technical/refund/complaint/all"
    )
    current_ticket_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="当前处理中的工单数"
    )
    max_ticket_count: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False,
        comment="最大同时处理工单数"
    )
    online_status: Mapped[str] = mapped_column(
        String(20), default="offline", nullable=False, index=True,
        comment="在线状态: online/busy/offline"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联用户
    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id], lazy="selectin")

    @property
    def is_available(self) -> bool:
        """是否可接单"""
        return (
            self.is_active
            and self.online_status == "online"
            and self.current_ticket_count < self.max_ticket_count
        )

    @property
    def load_ratio(self) -> float:
        """负载率 0.0 ~ 1.0"""
        if self.max_ticket_count == 0:
            return 1.0
        return self.current_ticket_count / self.max_ticket_count
