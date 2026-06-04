"""
KnowledgeService — 知识库服务。

功能:
    1. 导入知识库（从数据库加载到向量库）
    2. 相似度检索
    3. 管理知识条目
"""

import logging
from typing import Any

import faiss
import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeBase
from app.ai.services.vector_store import vector_store

logger = logging.getLogger(__name__)


class KnowledgeService:
    """知识库服务"""

    async def import_from_db(self, db: AsyncSession) -> int:
        """
        从数据库导入知识库到向量库。

        Returns:
            导入的知识条目数量
        """
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.is_active == True)
        )
        items = result.scalars().all()

        if not items:
            logger.info("[Knowledge] 数据库中无知识条目")
            return 0

        # 构建文档列表
        texts = []
        metadatas = []
        for item in items:
            # 将 question + answer 组合为文档内容
            doc_text = f"问题: {item.question}\n回答: {item.answer}"
            texts.append(doc_text)
            metadatas.append({
                "id": item.id,
                "question": item.question,
                "answer": item.answer,
                "category": item.category,
            })

        # 导入向量库
        count = vector_store.add_documents(
            texts=texts,
            metadatas=metadatas,
            chunk_size=1000,  # 知识库条目通常较短，不分块
            chunk_overlap=0,
        )

        logger.info("[Knowledge] 从数据库导入 %d 条知识", count)
        return count

    async def search(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        相似度检索。

        Args:
            query: 查询文本
            top_k: 返回前 K 个结果
            category: 按分类筛选

        Returns:
            检索结果列表
        """
        results = vector_store.search(query, top_k=top_k * 2)  # 多取一些用于筛选

        # 按分类筛选
        if category:
            results = [r for r in results if r.get("metadata", {}).get("category") == category]

        # 去重（基于 question）
        seen_questions = set()
        unique_results = []
        for r in results:
            q = r.get("metadata", {}).get("question", "")
            if q and q not in seen_questions:
                seen_questions.add(q)
                unique_results.append(r)

        # 截断到 top_k
        return unique_results[:top_k]

    async def add_knowledge(
        self,
        db: AsyncSession,
        question: str,
        answer: str,
        category: str = "general",
    ) -> int:
        """
        添加知识条目。

        Returns:
            新知识条目 ID
        """
        item = KnowledgeBase(
            question=question,
            answer=answer,
            category=category,
        )
        db.add(item)
        await db.flush()

        # 同步到向量库
        doc_text = f"问题: {question}\n回答: {answer}"
        vector_store.add_documents(
            texts=[doc_text],
            metadatas=[{
                "id": item.id,
                "question": question,
                "answer": answer,
                "category": category,
            }],
            chunk_size=1000,
            chunk_overlap=0,
        )

        await db.commit()
        logger.info("[Knowledge] 添加知识条目: id=%d", item.id)
        return item.id

    async def delete_knowledge(self, db: AsyncSession, knowledge_id: int) -> bool:
        """删除知识条目"""
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            return False

        await db.delete(item)
        await db.commit()
        logger.info("[Knowledge] 删除知识条目: id=%d", knowledge_id)
        return True

    def get_stats(self) -> dict:
        """获取向量库统计"""
        return {
            "total_documents": vector_store.doc_count,
        }


# ---- 全局单例 ----

knowledge_service = KnowledgeService()
