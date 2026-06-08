"""
阿里云 OSS 文件存储服务。

支持：
- 文件上传（图片、文档等）
- 文件删除
- 生成访问链接
"""

import logging
import os
from datetime import datetime
from typing import BinaryIO

import oss2
from oss2 import Bucket

from app.core.config import settings

logger = logging.getLogger(__name__)


class OSSService:
    """阿里云 OSS 服务"""

    def __init__(self):
        self._bucket: Bucket | None = None

    def _get_bucket(self) -> Bucket:
        """获取 OSS Bucket 实例（懒加载）"""
        if self._bucket is None:
            auth = oss2.Auth(
                settings.OSS_ACCESS_KEY_ID,
                settings.OSS_ACCESS_KEY_SECRET,
            )
            self._bucket = oss2.Bucket(
                auth,
                settings.OSS_ENDPOINT,
                settings.OSS_BUCKET_NAME,
            )
            logger.info("[OSS] 初始化完成: bucket=%s, endpoint=%s",
                       settings.OSS_BUCKET_NAME, settings.OSS_ENDPOINT)
        return self._bucket

    def _generate_key(self, folder: str, filename: str) -> str:
        """
        生成 OSS 文件 Key。

        格式: folder/YYYYMMDDHHMMSS_随机文件名.ext
        """
        now = datetime.now()
        date_prefix = now.strftime("%Y%m%d%H%M%S")
        # 保留原始文件扩展名
        ext = os.path.splitext(filename)[1].lower()
        # 清理文件名
        clean_name = "".join(c for c in os.path.splitext(filename)[0] if c.isalnum() or c in "-_")
        if not clean_name:
            clean_name = "file"
        return f"{folder}/{date_prefix}_{clean_name}{ext}"

    async def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        folder: str = "uploads",
        content_type: str | None = None,
    ) -> dict:
        """
        上传文件到 OSS。

        Args:
            file_data: 文件数据（二进制流）
            filename: 原始文件名
            folder: 存储目录（如 avatar, attachment, knowledge）
            content_type: 文件 MIME 类型

        Returns:
            包含 url, key, filename 的字典
        """
        bucket = self._get_bucket()
        key = self._generate_key(folder, filename)

        # 读取文件数据
        data = file_data.read()

        # 上传
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type

        bucket.put_object(key, data, headers=headers)

        # 生成访问 URL
        url = f"https://{settings.OSS_BUCKET_NAME}.{settings.OSS_ENDPOINT}/{key}"

        logger.info("[OSS] 上传成功: key=%s, size=%d bytes", key, len(data))

        return {
            "url": url,
            "key": key,
            "filename": filename,
            "size": len(data),
        }

    async def delete_file(self, key: str) -> bool:
        """
        删除 OSS 文件。

        Args:
            key: 文件的 OSS Key

        Returns:
            是否删除成功
        """
        try:
            bucket = self._get_bucket()
            bucket.delete_object(key)
            logger.info("[OSS] 删除成功: key=%s", key)
            return True
        except Exception as e:
            logger.error("[OSS] 删除失败: key=%s, error=%s", key, e)
            return False

    def get_file_url(self, key: str) -> str:
        """根据 key 生成文件访问 URL"""
        return f"https://{settings.OSS_BUCKET_NAME}.{settings.OSS_ENDPOINT}/{key}"


# 全局单例
oss_service = OSSService()
