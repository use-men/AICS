"""
Auth endpoints — client / CS / admin login.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.redis import (
    code_exists,
    generate_and_store_code,
    verify_code,
)
from app.core.security import (
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    AdminLoginStep1Request,
    AdminLoginStep2Request,
    CSLoginRequest,
    EmailLoginRequest,
    PhoneLoginRequest,
    RefreshTokenRequest,
    SendCodeRequest,
    TokenPairResponse,
    UserInfoResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ================================================================
#  Helpers
# ================================================================


def _build_user_info(user: User) -> dict:
    """Build user info dict from a User model."""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "roles": user.role_codes,
        "permissions": user.permission_codes,
        "employee_id": user.employee_id,
    }


# ================================================================
#  1. 客户端登录  POST /api/v1/auth/client/phone
# ================================================================


@router.post("/client/phone", response_model=TokenPairResponse)
async def client_phone_login(
    payload: PhoneLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPairResponse:
    """
    手机号 + 验证码登录（用户端）

    流程：
    1. 校验验证码
    2. 查找或自动注册用户
    3. 签发 JWT
    """
    # 1. 验证码校验
    ok = await verify_code(payload.phone, payload.code, purpose="client_login")
    if not ok:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 2. 查找用户（手机号）
    result = await db.execute(select(User).where(User.phone == payload.phone))
    user = result.scalar_one_or_none()

    # 自动注册（首次手机号登录）
    if user is None:
        user = User(
            username=f"user_{payload.phone[-4:]}",
            email=f"{payload.phone}@phone.smartdesk.local",
            phone=payload.phone,
            hashed_password=hash_password("phone_login_no_password"),
            nickname=f"用户{payload.phone[-4:]}",
        )
        db.add(user)
        await db.flush()

        # 分配 "user" 角色
        from app.models.user import Role
        role_result = await db.execute(select(Role).where(Role.code == "user"))
        user_role = role_result.scalar_one_or_none()
        if user_role:
            user.roles = [user_role]

        await db.commit()
        await db.refresh(user)
        logger.info("Auto-registered phone user: %s (id=%d)", payload.phone, user.id)

    # 3. 签发 token
    tokens = create_token_pair(user.id, extra={"roles": user.role_codes})
    return TokenPairResponse(**tokens)


# ================================================================
#  2. 客户端登录  POST /api/v1/auth/client/email
# ================================================================


@router.post("/client/email", response_model=TokenPairResponse)
async def client_email_login(
    payload: EmailLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPairResponse:
    """
    邮箱 + 密码登录（用户端）
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    tokens = create_token_pair(user.id, extra={"roles": user.role_codes})
    return TokenPairResponse(**tokens)


# ================================================================
#  3. 发送验证码  POST /api/v1/auth/send-code
# ================================================================


@router.post("/send-code")
async def send_verification_code(payload: SendCodeRequest):
    """
    发送短信验证码（通过 Spug 推送服务）
    """
    # 防刷：60 秒内不能重复发送
    if await code_exists(payload.phone, purpose="client_login"):
        raise HTTPException(status_code=429, detail="验证码已发送，请稍后再试")

    code = await generate_and_store_code(payload.phone, purpose="client_login")
    logger.info("Verification code for %s: %s", payload.phone, code)

    # 通过 Spug 推送验证码（GET 方式，模板参数: code=验证码, number=手机号）
    import httpx
    push_url = "https://push.spug.cc/send/yWYXwm6LwErb1VZ2"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(push_url, params={
                "code": code,
                "number": payload.phone,
            })
            logger.info("[Push] 推送结果: %s", resp.text[:200])
    except Exception as e:
        logger.error("[Push] 推送失败: %s", e)

    return {"message": "验证码已发送"}


# ================================================================
#  4. 客服端登录  POST /api/v1/auth/cs/login
# ================================================================


@router.post("/cs/login", response_model=TokenPairResponse)
async def cs_login(
    payload: CSLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPairResponse:
    """
    客服端登录：工号 + 密码

    校验：
    1. 通过 employee_id 查找用户
    2. 校验密码
    3. 检查是否有 customer_service / agent / supervisor 角色
    4. 签发 JWT（含角色和权限）
    """
    result = await db.execute(select(User).where(User.employee_id == payload.employee_id))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="工号或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    # 检查客服角色
    cs_roles = {"customer_service", "agent", "supervisor"}
    if not cs_roles.intersection(set(user.role_codes)):
        raise HTTPException(status_code=403, detail="该账号没有客服权限")

    tokens = create_token_pair(
        user.id,
        extra={
            "roles": user.role_codes,
            "permissions": user.permission_codes,
            "login_type": "cs",
        },
    )
    return TokenPairResponse(**tokens)


# ================================================================
#  5. 管理端登录 Step 1  POST /api/v1/auth/admin/login
# ================================================================


@router.post("/admin/login")
async def admin_login_step1(
    payload: AdminLoginStep1Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    管理端登录第一步：账号密码校验 → 发送邮箱验证码

    返回：
    - success → 验证码已发送
    - 失败 → 400/403
    """
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="账号或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    # 检查管理员角色
    admin_roles = {"admin", "supervisor", "finance"}
    if not admin_roles.intersection(set(user.role_codes)):
        raise HTTPException(status_code=403, detail="该账号没有管理权限")

    # 发送邮箱验证码（防刷 60s）
    if await code_exists(user.email, purpose="admin_verify"):
        raise HTTPException(status_code=429, detail="验证码已发送，请稍后再试")

    code = await generate_and_store_code(user.email, purpose="admin_verify")
    logger.info("Admin verify code for %s: %s", user.email, code)
    # 生产环境这里调用邮件 SDK

    return {
        "message": "验证码已发送至管理员邮箱",
        "email_masked": _mask_email(user.email),
        "code": code,  # 开发环境返回验证码
    }


# ================================================================
#  6. 管理端登录 Step 2  POST /api/v1/auth/admin/verify
# ================================================================


@router.post("/admin/verify", response_model=TokenPairResponse)
async def admin_login_step2(
    payload: AdminLoginStep2Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPairResponse:
    """
    管理端登录第二步：邮箱验证码校验 → 签发高权限 JWT
    """
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=400, detail="用户不存在")

    # 验证码校验
    ok = await verify_code(user.email, payload.code, purpose="admin_verify")
    if not ok:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    tokens = create_token_pair(
        user.id,
        extra={
            "roles": user.role_codes,
            "permissions": user.permission_codes,
            "login_type": "admin",
        },
    )
    return TokenPairResponse(**tokens)


# ================================================================
#  7. 刷新 Token  POST /api/v1/auth/refresh
# ================================================================


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPairResponse:
    """使用 refresh_token 换取新的 token pair"""
    token_data = decode_token(payload.refresh_token)
    if token_data is None or token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token 无效或已过期")

    user_id = int(token_data["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    tokens = create_token_pair(user.id, extra={"roles": user.role_codes})
    return TokenPairResponse(**tokens)


# ================================================================
#  8. 获取当前用户  GET /api/v1/auth/me
# ================================================================


@router.get("/me", response_model=UserInfoResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserInfoResponse:
    """获取当前登录用户信息"""
    return UserInfoResponse(**_build_user_info(current_user))


# ================================================================
#  9. 退出登录  POST /api/v1/auth/logout
# ================================================================


@router.post("/logout")
async def logout():
    """退出登录（客户端清除 token 即可）"""
    return {"message": "已退出登录"}


# ================================================================
#  Helpers
# ================================================================


def _mask_email(email: str) -> str:
    """Mask email for display: a***@example.com"""
    parts = email.split("@")
    if len(parts) != 2:
        return email
    name, domain = parts
    if len(name) <= 1:
        return f"*@{domain}"
    return f"{name[0]}***@{domain}"
