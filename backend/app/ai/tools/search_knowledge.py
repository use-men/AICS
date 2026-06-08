"""
search_knowledge_tool — 知识库搜索工具。

调用知识库检索相关信息。
"""

import logging

from app.ai.tools.base import BaseTool, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class SearchKnowledgeTool(BaseTool):
    """知识库搜索工具"""

    @property
    def name(self) -> str:
        return "search_knowledge"

    @property
    def description(self) -> str:
        return "搜索知识库，获取相关问题的答案和信息"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="str",
                description="搜索关键词或问题",
                required=True,
            ),
            ToolParameter(
                name="top_k",
                type="int",
                description="返回结果数量",
                required=False,
                default=5,
            ),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        """
        执行知识库搜索。

        Args:
            query: 搜索关键词
            top_k: 返回结果数量

        Returns:
            ToolResult 包含搜索结果
        """
        query = kwargs.get("query")
        if not query:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="缺少必填参数: query",
            )

        top_k = kwargs.get("top_k", 5)

        try:
            from app.ai.services.knowledge_service import knowledge_service

            logger.info("[SearchKnowledge] 搜索: %s (top_k=%d)", query, top_k)

            # 调用知识库服务
            search_results = await knowledge_service.search(query, top_k=top_k)

            # 格式化结果
            results = []
            for i, result in enumerate(search_results, 1):
                meta = result.get("metadata", {})
                results.append({
                    "index": i,
                    "question": meta.get("question", ""),
                    "answer": meta.get("answer", ""),
                    "score": round(result.get("score", 0), 3),
                })

            data = {
                "query": query,
                "total": len(results),
                "results": results,
            }

            logger.info("[SearchKnowledge] 搜索完成: %s (找到 %d 条结果)", query, len(results))
            return ToolResult(status=ToolStatus.SUCCESS, data=data)

        except Exception as e:
            logger.error("[SearchKnowledge] 搜索失败: %s", e)
            return ToolResult(status=ToolStatus.ERROR, error=str(e))


# ---- 全局单例 ----

search_knowledge_tool = SearchKnowledgeTool()