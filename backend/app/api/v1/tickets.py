"""
Tickets API — 工单系统完整 CRUD。
"""

import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import decode_token
from app.models.user import User
from app.models.ticket import Ticket, TicketReply

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["Tickets"])


# ============================================================
#  Schemas
# ============================================================

class TicketCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    ticket_type: str = Field(..., pattern="^(after_sales|technical|refund|complaint)$")

class TicketUpdateStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|assigned|processing|resolved|closed)$")

class TicketAssignRequest(BaseModel):
    service_id: int

class TicketReplyRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class TicketOut(BaseModel):
    id: int
    ticket_no: str
    title: str
    content: str
    ticket_type: str
    priority: str
    status: str
    user_id: int
    service_id: int | None
    created_at: str | None
    updated_at: str | None
    reply_count: int = 0

class TicketDetailOut(TicketOut):
    replies: list[dict] = []

class StatsOut(BaseModel):
    total: int = 0
    pending: int = 0
    assigned: int = 0
    processing: int = 0
    resolved: int = 0
    closed: int = 0
    by_type: dict[str, int] = {}
    by_priority: dict[str, int] = {}

def _gen_ticket_no(ticket_id: int) -> str:
    return f"TK{ticket_id:06d}"


def _ticket_to_dict(t: Ticket, reply_count: int = 0) -> dict:
    return {
        "id": t.id,
        "ticket_no": t.ticket_no,
        "title": t.title,
        "content": t.content,
        "ticket_type": t.ticket_type,
        "priority": t.priority,
        "status": t.status,
        "user_id": t.user_id,
        "service_id": t.service_id,
        "created_at": str(t.created_at) if t.created_at else None,
        "updated_at": str(t.updated_at) if t.updated_at else None,
        "reply_count": reply_count,
    }


# ============================================================
#  1. 创建工单（用户端）
# ============================================================

@router.post("", response_model=TicketOut, status_code=201)
async def create_ticket(
    payload: TicketCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = Ticket(
        ticket_no="",
        title=payload.title,
        content=payload.content,
        ticket_type=payload.ticket_type,
        priority="medium",
        status="pending",
        user_id=current_user.id,
    )
    db.add(ticket)
    await db.flush()
    ticket.ticket_no = _gen_ticket_no(ticket.id)
    await db.commit()
    await db.refresh(ticket)
    return _ticket_to_dict(ticket)


# ============================================================
#  2. 工单列表（支持筛选）
# ============================================================

@router.get("")
async def list_tickets(
    status: str | None = None,
    ticket_type: str | None = None,
    priority: str | None = None,
    user_id: int | None = None,
    service_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Ticket, func.count(TicketReply.id).label("reply_count")).outerjoin(TicketReply).group_by(Ticket.id)
    count_query = select(func.count(Ticket.id))

    # 权限过滤
    is_admin = "admin" in current_user.role_codes
    is_cs = bool(set(current_user.role_codes) & {"customer_service", "agent", "supervisor"})

    if not is_admin and not is_cs:
        query = query.where(Ticket.user_id == current_user.id)
        count_query = count_query.where(Ticket.user_id == current_user.id)

    if status:
        query = query.where(Ticket.status == status)
        count_query = count_query.where(Ticket.status == status)
    if ticket_type:
        query = query.where(Ticket.ticket_type == ticket_type)
        count_query = count_query.where(Ticket.ticket_type == ticket_type)
    if priority:
        query = query.where(Ticket.priority == priority)
        count_query = count_query.where(Ticket.priority == priority)
    if user_id:
        query = query.where(Ticket.user_id == user_id)
        count_query = count_query.where(Ticket.user_id == user_id)
    if service_id:
        query = query.where(Ticket.service_id == service_id)
        count_query = count_query.where(Ticket.service_id == service_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(Ticket.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    tickets = [_ticket_to_dict(t, rc) for t, rc in rows]

    return {"data": tickets, "total": total, "page": page, "page_size": page_size}


# ============================================================
#  3. 工单详情
# ============================================================

@router.get("/{ticket_id}", response_model=TicketDetailOut)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    # 查询回复
    reply_result = await db.execute(
        select(TicketReply).where(TicketReply.ticket_id == ticket_id).order_by(TicketReply.created_at)
    )
    replies = reply_result.scalars().all()

    data = _ticket_to_dict(ticket, len(replies))
    data["replies"] = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "role": r.role,
            "content": r.content,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in replies
    ]
    return data


# ============================================================
#  4. 更新工单状态
# ============================================================

@router.put("/{ticket_id}/status")
async def update_status(
    ticket_id: int,
    payload: TicketUpdateStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    ticket.status = payload.status
    await db.commit()
    return {"message": "状态已更新", "ticket_id": ticket_id, "status": payload.status}


# ============================================================
#  5. 客服接单
# ============================================================

@router.put("/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: int,
    payload: TicketAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    ticket.service_id = payload.service_id
    ticket.status = "assigned"
    await db.commit()
    return {"message": "工单已分配", "ticket_id": ticket_id, "service_id": payload.service_id}


# ============================================================
#  6. 客服接单（当前用户接单）
# ============================================================

@router.put("/{ticket_id}/accept")
async def accept_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    ticket.service_id = current_user.id
    ticket.status = "processing"
    await db.commit()
    return {"message": "已接单", "ticket_id": ticket_id}


# ============================================================
#  7. 回复工单
# ============================================================

_bearer = HTTPBearer(auto_error=False)


@router.post("/{ticket_id}/replies")
async def create_reply(
    ticket_id: int,
    payload: TicketReplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    # ---- 多信号综合判断角色 ----
    token = credentials.credentials if credentials else ""
    role = _detect_reply_role(current_user, token)

    reply = TicketReply(
        ticket_id=ticket_id,
        user_id=current_user.id,
        role=role,
        content=payload.content,
    )
    db.add(reply)
    await db.commit()

    return {"message": "回复成功", "reply_id": reply.id}


def _detect_reply_role(user: User, token: str = "") -> str:
    """
    多信号综合判断回复者角色。

    判断优先级:
    1. JWT login_type（登录时确定，最可靠）
    2. 数据库角色码（RBAC 系统角色）
    3. employee_id（有工号 = 客服人员）
    4. 默认 user
    """
    # 信号1: JWT 中的 login_type（CS/Admin 登录时写入）
    if token:
        payload = decode_token(token)
        if payload:
            login_type = payload.get("login_type")
            if login_type == "admin":
                return "admin"
            if login_type == "cs":
                return "service"

    # 信号2: 数据库角色码
    role_codes = set(user.role_codes)
    if "admin" in role_codes:
        return "admin"
    if role_codes & {"customer_service", "agent", "supervisor"}:
        return "service"

    # 信号3: 有 employee_id 说明是客服人员
    if user.employee_id:
        return "service"

    # 信号4: 默认普通用户
    return "user"


# ============================================================
#  8. 工单统计（管理端）
# ============================================================

@router.get("/stats/overview")
async def ticket_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 总数
    total = (await db.execute(select(func.count(Ticket.id)))).scalar() or 0

    # 各状态数量
    async def count_by_status(s: str) -> int:
        r = await db.execute(select(func.count(Ticket.id)).where(Ticket.status == s))
        return r.scalar() or 0

    pending = await count_by_status("pending")
    assigned = await count_by_status("assigned")
    processing = await count_by_status("processing")
    resolved = await count_by_status("resolved")
    closed = await count_by_status("closed")

    # 按类型统计
    type_result = await db.execute(
        select(Ticket.ticket_type, func.count(Ticket.id)).group_by(Ticket.ticket_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    # 按优先级统计
    priority_result = await db.execute(
        select(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority)
    )
    by_priority = {row[0]: row[1] for row in priority_result.all()}

    return {
        "total": total,
        "pending": pending,
        "assigned": assigned,
        "processing": processing,
        "resolved": resolved,
        "closed": closed,
        "by_type": by_type,
        "by_priority": by_priority,
    }


# ============================================================
#  9. 管理端 AI 运营大屏统计
# ============================================================

from datetime import datetime, timedelta, timezone
from sqlalchemy import and_


@router.get("/stats/dashboard")
async def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    管理端 AI 运营大屏统计。

    返回: 工单趋势、AI解决率、派单率、转人工率、响应时间、客服排行
    """
    now = datetime.now(timezone.utc)

    # ---- 基础统计 ----
    total = (await db.execute(select(func.count(Ticket.id)))).scalar() or 0

    async def count_by_status(s: str) -> int:
        r = await db.execute(select(func.count(Ticket.id)).where(Ticket.status == s))
        return r.scalar() or 0

    pending = await count_by_status("pending")
    assigned = await count_by_status("assigned")
    processing = await count_by_status("processing")
    resolved = await count_by_status("resolved")
    closed = await count_by_status("closed")

    # ---- 近7天工单趋势 ----
    dates = []
    trend_counts = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        r = await db.execute(
            select(func.count(Ticket.id)).where(
                and_(Ticket.created_at >= day_start, Ticket.created_at < day_end)
            )
        )
        count = r.scalar() or 0
        dates.append(day_start.strftime("%m-%d"))
        trend_counts.append(count)

    # ---- 按类型统计 ----
    type_result = await db.execute(
        select(Ticket.ticket_type, func.count(Ticket.id)).group_by(Ticket.ticket_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    # ---- 按优先级统计 ----
    priority_result = await db.execute(
        select(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority)
    )
    by_priority = {row[0]: row[1] for row in priority_result.all()}

    # ---- 按状态统计 ----
    by_status = {
        "pending": pending,
        "assigned": assigned,
        "processing": processing,
        "resolved": resolved,
        "closed": closed,
    }

    # ---- AI 解决率 ----
    # 已解决工单总数
    resolved_total = resolved + closed
    # 有 AI 消息参与的已解决工单（TicketMessage.sender_type = 'ai'）
    from app.models.ticket_message import TicketMessage
    ai_resolved_result = await db.execute(
        select(func.count(func.distinct(TicketMessage.ticket_id))).join(
            Ticket, Ticket.id == TicketMessage.ticket_id
        ).where(
            and_(
                TicketMessage.sender_type == "ai",
                Ticket.status.in_(["resolved", "closed"]),
            )
        )
    )
    ai_resolved = ai_resolved_result.scalar() or 0
    ai_resolve_rate = round(ai_resolved / resolved_total, 2) if resolved_total > 0 else 0

    # ---- 自动派单率 ----
    # 有 service_id 的工单 / 总工单
    assigned_count = (await db.execute(
        select(func.count(Ticket.id)).where(Ticket.service_id.isnot(None))
    )).scalar() or 0
    auto_dispatch_rate = round(assigned_count / total, 2) if total > 0 else 0

    # ---- 转人工率 ----
    # 从 AI 聊天转来的工单（标题包含 "用户咨询" 或 content 来自 AI 转人工创建）
    # 这里用 TicketMessage 中有 ai 类型消息且工单来自 agent 创建来判断
    from app.models.ticket_message import TicketMessage
    transfer_result = await db.execute(
        select(func.count(func.distinct(TicketMessage.ticket_id))).join(
            Ticket, Ticket.id == TicketMessage.ticket_id
        ).where(
            and_(
                TicketMessage.sender_type == "ai",
                Ticket.service_id.isnot(None),
            )
        )
    )
    transfer_count = transfer_result.scalar() or 0
    transfer_rate = round(transfer_count / total, 2) if total > 0 else 0

    # ---- 平均响应时间（分钟）----
    # 首条客服回复时间 - 工单创建时间
    from app.models.ticket import TicketReply
    # 获取所有有回复的工单
    tickets_with_replies = await db.execute(
        select(Ticket.id, Ticket.created_at).where(
            Ticket.id.in_(
                select(TicketReply.ticket_id).distinct()
            )
        )
    )
    total_response_seconds = 0
    response_count = 0
    for ticket_row in tickets_with_replies.all():
        ticket_id, ticket_created = ticket_row
        # 查找该工单的第一条客服回复
        first_reply = await db.execute(
            select(TicketReply.created_at).where(
                and_(TicketReply.ticket_id == ticket_id, TicketReply.role == "service")
            ).order_by(TicketReply.created_at.asc()).limit(1)
        )
        first_reply_row = first_reply.first()
        if first_reply_row and ticket_created:
            reply_time = first_reply_row[0]
            if reply_time and ticket_created:
                # 确保都有时区信息
                if reply_time.tzinfo is None:
                    reply_time = reply_time.replace(tzinfo=timezone.utc)
                if ticket_created.tzinfo is None:
                    ticket_created = ticket_created.replace(tzinfo=timezone.utc)
                diff = (reply_time - ticket_created).total_seconds()
                if diff >= 0:
                    total_response_seconds += diff
                    response_count += 1

    avg_first_response = round(total_response_seconds / response_count / 60, 1) if response_count > 0 else 0

    # ---- 平均解决时长（分钟）----
    resolved_tickets = await db.execute(
        select(Ticket.created_at, Ticket.updated_at).where(
            Ticket.status.in_(["resolved", "closed"])
        )
    )
    total_resolve_seconds = 0
    resolve_count = 0
    for row in resolved_tickets.all():
        created, updated = row
        if created and updated:
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            diff = (updated - created).total_seconds()
            if diff >= 0:
                total_resolve_seconds += diff
                resolve_count += 1

    avg_resolve_minutes = round(total_resolve_seconds / resolve_count / 60, 1) if resolve_count > 0 else 0

    # ---- 客服排行 ----
    from app.models.customer_service import CustomerService
    agent_result = await db.execute(
        select(
            CustomerService.name,
            func.count(Ticket.id).label("ticket_count"),
        ).join(
            Ticket, Ticket.service_id == CustomerService.id
        ).where(
            Ticket.status.in_(["resolved", "closed"])
        ).group_by(
            CustomerService.id, CustomerService.name
        ).order_by(
            func.count(Ticket.id).desc()
        ).limit(10)
    )
    agent_ranking = [
        {"name": row[0], "resolved": row[1]}
        for row in agent_result.all()
    ]

    return {
        "total": total,
        "pending": pending,
        "assigned": assigned,
        "processing": processing,
        "resolved": resolved,
        "closed": closed,
        "trend": {"dates": dates, "counts": trend_counts},
        "ai_resolve_rate": ai_resolve_rate,
        "auto_dispatch_rate": auto_dispatch_rate,
        "transfer_rate": transfer_rate,
        "avg_first_response_minutes": avg_first_response,
        "avg_resolve_minutes": avg_resolve_minutes,
        "by_type": by_type,
        "by_priority": by_priority,
        "by_status": by_status,
        "agent_ranking": agent_ranking,
    }
