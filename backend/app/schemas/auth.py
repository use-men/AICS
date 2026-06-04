"""
Auth request / response schemas.
"""

from pydantic import BaseModel, EmailStr, Field


# ======== Client Login ========

class PhoneLoginRequest(BaseModel):
    """手机号 + 验证码登录"""
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")
    code: str = Field(..., min_length=6, max_length=6, description="6位验证码")


class EmailLoginRequest(BaseModel):
    """邮箱 + 密码登录"""
    email: EmailStr
    password: str = Field(..., min_length=6)


class SendCodeRequest(BaseModel):
    """发送验证码"""
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")


# ======== CS Login ========

class CSLoginRequest(BaseModel):
    """客服端：工号 + 密码"""
    employee_id: str = Field(..., min_length=5, description="工号，如 cs_1001")
    password: str = Field(..., min_length=6)


# ======== Admin Login ========

class AdminLoginStep1Request(BaseModel):
    """管理端第一步：账号 + 密码"""
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)


class AdminLoginStep2Request(BaseModel):
    """管理端第二步：邮箱验证码"""
    username: str = Field(..., min_length=3)
    code: str = Field(..., min_length=6, max_length=6)


# ======== Token ========

class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserInfoResponse(BaseModel):
    id: int
    username: str
    email: str
    phone: str | None = None
    nickname: str | None = None
    avatar: str | None = None
    roles: list[str]
    permissions: list[str]
    employee_id: str | None = None

    class Config:
        from_attributes = True
