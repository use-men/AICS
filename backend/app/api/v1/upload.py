"""
文件上传 API — 支持头像、附件、知识库文档等。
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.core.oss import oss_service
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Upload"])

# 允许的文件类型
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_DOC_TYPES = {"application/pdf", "application/msword",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     "text/plain", "text/markdown"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_DOC_TYPES

# 文件大小限制（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024


class UploadResponse(BaseModel):
    """上传响应"""
    url: str
    key: str
    filename: str
    size: int


# ================================================================
#  1. 通用文件上传  POST /api/v1/upload/file
# ================================================================


@router.post("/file", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Form("uploads"),
    current_user: User = Depends(get_current_user),
):
    """
    上传文件到 OSS。

    - folder: 存储目录（avatar/attachment/knowledge）
    - 支持格式：图片（jpg/png/gif/webp）、文档（pdf/doc/txt/md）
    - 大小限制：10MB
    """
    # 1. 检查文件类型
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}",
        )

    # 2. 检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）",
        )

    # 3. 上传到 OSS
    try:
        import io
        file_data = io.BytesIO(content)
        result = await oss_service.upload_file(
            file_data=file_data,
            filename=file.filename or "unknown",
            folder=folder,
            content_type=file.content_type,
        )
        logger.info("[Upload] 用户 %d 上传文件: %s", current_user.id, result["key"])
        return UploadResponse(**result)
    except Exception as e:
        logger.error("[Upload] 上传失败: %s", e)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


# ================================================================
#  2. 头像上传  POST /api/v1/upload/avatar
# ================================================================


@router.post("/avatar", response_model=UploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    上传用户头像。

    - 仅支持图片格式
    - 大小限制：5MB
    """
    # 1. 检查文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"头像仅支持图片格式（jpg/png/gif/webp）",
        )

    # 2. 检查文件大小（头像限制 5MB）
    content = await file.read()
    max_avatar_size = 5 * 1024 * 1024
    if len(content) > max_avatar_size:
        raise HTTPException(
            status_code=400,
            detail=f"头像大小超过限制（最大 5MB）",
        )

    # 3. 上传到 OSS
    try:
        import io
        file_data = io.BytesIO(content)
        result = await oss_service.upload_file(
            file_data=file_data,
            filename=file.filename or "avatar",
            folder="avatar",
            content_type=file.content_type,
        )

        # 4. 更新用户头像
        current_user.avatar = result["url"]
        from app.core.database import async_session_factory
        async with async_session_factory() as session:
            await session.merge(current_user)
            await session.commit()

        logger.info("[Upload] 用户 %d 更新头像: %s", current_user.id, result["url"])
        return UploadResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Upload] 头像上传失败: %s", e)
        raise HTTPException(status_code=500, detail=f"头像上传失败: {str(e)}")


# ================================================================
#  3. 删除文件  DELETE /api/v1/upload/file
# ================================================================


@router.delete("/file")
async def delete_file(
    key: str,
    current_user: User = Depends(get_current_user),
):
    """删除 OSS 文件"""
    success = await oss_service.delete_file(key)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    return {"message": "删除成功"}
