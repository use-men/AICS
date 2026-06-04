"""
Knowledge API — 知识库管理接口。
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.knowledge import KnowledgeBase
from app.ai.services.knowledge_service import knowledge_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


# ---- Schemas ----

class KnowledgeCreateRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    answer: str = Field(..., min_length=1, max_length=5000)
    category: str = Field(default="general", max_length=50)

class KnowledgeBatchImportRequest(BaseModel):
    items: list[KnowledgeCreateRequest] = Field(..., min_length=1, max_length=500)

class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    category: str | None = None

class KnowledgeOut(BaseModel):
    id: int
    question: str
    answer: str
    category: str
    is_active: bool
    created_at: str | None


# ---- 1. 搜索知识库 ----

@router.post("/search")
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """相似度检索知识库，返回 Top K 结果"""
    try:
        results = await knowledge_service.search(
            query=payload.query,
            top_k=payload.top_k,
            category=payload.category,
        )
        return {"results": results, "total": len(results)}
    except Exception as e:
        logger.error("[Knowledge API] 搜索失败: %s", e)
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


# ---- 2. 添加知识条目 ----

@router.post("", status_code=201)
async def add_knowledge(
    payload: KnowledgeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加单条知识"""
    try:
        kid = await knowledge_service.add_knowledge(
            db=db,
            question=payload.question,
            answer=payload.answer,
            category=payload.category,
        )
        return {"id": kid, "message": "添加成功"}
    except Exception as e:
        logger.error("[Knowledge API] 添加失败: %s", e)
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


# ---- 3. 批量导入 ----

@router.post("/batch")
async def batch_import(
    payload: KnowledgeBatchImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量导入知识条目"""
    try:
        ids = []
        for item in payload.items:
            kid = await knowledge_service.add_knowledge(
                db=db,
                question=item.question,
                answer=item.answer,
                category=item.category,
            )
            ids.append(kid)
        return {"imported": len(ids), "ids": ids}
    except Exception as e:
        logger.error("[Knowledge API] 批量导入失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e) or repr(e)}")


# ---- 4. 从数据库加载到向量库 ----

@router.post("/load")
async def load_from_db(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从数据库加载知识到向量库"""
    try:
        count = await knowledge_service.import_from_db(db)
        return {"loaded": count, "message": f"已加载 {count} 条知识"}
    except Exception as e:
        logger.error("[Knowledge API] 加载失败: %s", e)
        raise HTTPException(status_code=500, detail=f"加载失败: {str(e)}")


# ---- 5. 知识库列表 ----

@router.get("")
async def list_knowledge(
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库列表"""
    query = select(KnowledgeBase)
    count_query = select(func.count(KnowledgeBase.id))

    if category:
        query = query.where(KnowledgeBase.category == category)
        count_query = count_query.where(KnowledgeBase.category == category)

    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(KnowledgeBase.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "data": [
            {
                "id": item.id,
                "question": item.question,
                "answer": item.answer,
                "category": item.category,
                "is_active": item.is_active,
                "created_at": str(item.created_at) if item.created_at else None,
            }
            for item in items
        ],
        "total": total,
    }


# ---- 6. 删除知识条目 ----

@router.delete("/{knowledge_id}")
async def delete_knowledge(
    knowledge_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除知识条目"""
    ok = await knowledge_service.delete_knowledge(db, knowledge_id)
    if not ok:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    return {"message": "删除成功"}


# ---- 7. 知识库统计 ----

@router.get("/stats")
async def knowledge_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库统计"""
    total_db = (await db.execute(select(func.count(KnowledgeBase.id)))).scalar() or 0
    vector_stats = knowledge_service.get_stats()

    return {
        "total_in_db": total_db,
        "total_in_vector": vector_stats["total_documents"],
    }
