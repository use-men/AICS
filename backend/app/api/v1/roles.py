"""
Roles API — 角色管理 CRUD。
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import Role, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/roles", tags=["角色管理"])


# ============================================================
#  Schemas
# ============================================================


class RoleCreateRequest(BaseModel):
    """创建角色请求"""
    name: str = Field(..., min_length=1, max_length=50, description="角色名称")
    code: str = Field(..., min_length=1, max_length=50, description="角色编码")
    description: str | None = Field(default=None, description="角色描述")


class RoleUpdateRequest(BaseModel):
    """更新角色请求"""
    name: str | None = Field(default=None, min_length=1, max_length=50, description="角色名称")
    description: str | None = Field(default=None, description="角色描述")


class RoleResponse(BaseModel):
    """角色响应"""
    id: int
    name: str
    code: str
    description: str | None
    user_count: int = 0


# ============================================================
#  预设角色（不可删除）
# ============================================================

BUILTIN_ROLES = {"admin", "agent", "user"}


# ============================================================
#  API Endpoints
# ============================================================


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RoleResponse]:
    """获取角色列表"""
    result = await db.execute(select(Role).order_by(Role.id))
    roles = result.scalars().all()

    return [
        RoleResponse(
            id=role.id,
            name=role.name,
            code=role.code,
            description=role.description,
            user_count=len(role.users) if role.users else 0,
        )
        for role in roles
    ]


@router.post("", response_model=RoleResponse)
async def create_role(
    payload: RoleCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoleResponse:
    """创建角色"""
    # 检查 code 唯一性
    existing = await db.execute(select(Role).where(Role.code == payload.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="角色编码已存在")

    # 检查 name 唯一性
    existing_name = await db.execute(select(Role).where(Role.name == payload.name))
    if existing_name.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="角色名称已存在")

    role = Role(
        name=payload.name,
        code=payload.code,
        description=payload.description,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    logger.info("[Role] 创建角色: %s (%s)", role.name, role.code)

    return RoleResponse(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        user_count=0,
    )


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    payload: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoleResponse:
    """更新角色"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 内置角色不允许修改 code
    if role.code in BUILTIN_ROLES and payload.name:
        # 内置角色可以修改 name，但不能修改 code
        pass

    # 检查 name 唯一性
    if payload.name and payload.name != role.name:
        existing_name = await db.execute(select(Role).where(Role.name == payload.name))
        if existing_name.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="角色名称已存在")
        role.name = payload.name

    if payload.description is not None:
        role.description = payload.description

    await db.commit()
    await db.refresh(role)

    logger.info("[Role] 更新角色: %s (%s)", role.name, role.code)

    return RoleResponse(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        user_count=len(role.users) if role.users else 0,
    )


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """删除角色"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 内置角色不可删除
    if role.code in BUILTIN_ROLES:
        raise HTTPException(status_code=400, detail=f"内置角色 {role.code} 不可删除")

    # 检查是否有用户使用此角色
    if role.users and len(role.users) > 0:
        raise HTTPException(status_code=400, detail="该角色下有用户，无法删除")

    await db.delete(role)
    await db.commit()

    logger.info("[Role] 删除角色: %s (%s)", role.name, role.code)

    return {"message": "删除成功"}
