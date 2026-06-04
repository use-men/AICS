"""
Dispatch API — 自动派单接口。
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.ai.services.dispatch_service import dispatch_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dispatch", tags=["Dispatch"])


# ---- Schemas ----

class DispatchRequest(BaseModel):
    """派单请求"""
    ticket_id: int = Field(..., description="工单ID")
    ticket_type: str = Field(..., description="工单类型: after_sales/technical/refund/complaint")

class DispatchResponse(BaseModel):
    """派单响应"""
    service_id: int
    service_name: str
    skill_type: str
    score: float

class DispatchErrorResponse(BaseModel):
    """派单失败响应"""
    error: str


# ---- 1. 自动派单 ----

@router.post("/auto", response_model=DispatchResponse)
async def auto_dispatch(
    payload: DispatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    自动派单。

    根据工单类型自动匹配最合适的客服:
    - 技能匹配
    - 在线状态
    - 工单最少
    """
    try:
        result = await dispatch_service.auto_dispatch(
            ticket_id=payload.ticket_id,
            ticket_type=payload.ticket_type,
            db=db,
        )

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return DispatchResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Dispatch API] 派单失败: %s", e)
        raise HTTPException(status_code=500, detail=f"派单失败: {str(e)}")


# ---- 2. 获取可用客服列表 ----

@router.get("/agents")
async def get_available_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有可用客服"""
    try:
        agents = await dispatch_service.get_available_agents(db)
        return {"agents": agents, "total": len(agents)}
    except Exception as e:
        logger.error("[Dispatch API] 获取客服失败: %s", e)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


# ---- 3. 派单统计 ----

@router.get("/stats")
async def dispatch_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取派单统计"""
    try:
        stats = await dispatch_service.get_dispatch_stats(db)
        return stats
    except Exception as e:
        logger.error("[Dispatch API] 统计失败: %s", e)
        raise HTTPException(status_code=500, detail=f"统计失败: {str(e)}")
