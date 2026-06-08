"""
search_web_tool — 联网搜索工具。

调用 Tavily API 搜索互联网信息。
"""

import json
import logging

from app.ai.tools.base import BaseTool, ToolParameter, ToolResult, ToolStatus
from app.ai.config import ai_settings

logger = logging.getLogger(__name__)


class SearchWebTool(BaseTool):
    """联网搜索工具"""

    @property
    def name(self) -> str:
        return "search_web"

    @property
    def description(self) -> str:
        return "搜索互联网获取最新信息，包括新闻、知识、实时数据等"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="str",
                description="搜索关键词",
                required=True,
            ),
            ToolParameter(
                name="max_results",
                type="int",
                description="最大返回结果数",
                required=False,
                default=5,
            ),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        """
        执行联网搜索。

        Args:
            query: 搜索关键词
            max_results: 最大返回结果数

        Returns:
            ToolResult 包含搜索结果
        """
        query = kwargs.get("query")
        if not query:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="缺少必填参数: query",
            )

        max_results = kwargs.get("max_results", ai_settings.WEB_SEARCH_MAX_RESULTS)

        # 检查 API Key
        if not ai_settings.TAVILY_API_KEY:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="搜索服务未配置（TAVILY_API_KEY 未设置）",
            )

        try:
            from tavily import AsyncTavilyClient

            logger.info("[SearchWeb] 搜索: %s (max_results=%d)", query, max_results)

            client = AsyncTavilyClient(api_key=ai_settings.TAVILY_API_KEY)
            response = await client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
            )

            # 格式化结果
            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", "")[:500],
                })

            data = {
                "query": query,
                "total": len(results),
                "results": results,
            }

            logger.info("[SearchWeb] 搜索完成: %s (找到 %d 条结果)", query, len(results))
            return ToolResult(status=ToolStatus.SUCCESS, data=data)

        except ImportError:
            logger.error("[SearchWeb] tavily-python 未安装")
            return ToolResult(
                status=ToolStatus.ERROR,
                error="搜索依赖未安装，请运行: pip install tavily-python",
            )
        except Exception as e:
            logger.error("[SearchWeb] 搜索失败: %s", e)
            return ToolResult(status=ToolStatus.ERROR, error=str(e))


# ---- 全局单例 ----

search_web_tool = SearchWebTool()