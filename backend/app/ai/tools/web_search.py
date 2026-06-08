"""
联网搜索工具 - 使用 Tavily API 搜索互联网信息。

当知识库检索置信度低时，自动触发联网搜索补充信息。
"""

import json
import logging
from typing import Any

from app.ai.config import ai_settings

logger = logging.getLogger(__name__)


async def web_search(query: str) -> str:
    """
    搜索互联网获取最新信息。

    Args:
        query: 搜索关键词

    Returns:
        搜索结果的 JSON 字符串，包含 query, results, total 字段
    """
    if not ai_settings.TAVILY_API_KEY:
        logger.warning("[WebSearch] TAVILY_API_KEY 未配置，跳过联网搜索")
        return json.dumps({
            "query": query,
            "results": [],
            "total": 0,
            "error": "搜索服务未配置",
        }, ensure_ascii=False)

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=ai_settings.TAVILY_API_KEY)
        response = await client.search(
            query=query,
            max_results=ai_settings.WEB_SEARCH_MAX_RESULTS,
            search_depth="basic",
        )

        # 格式化结果
        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", "")[:500],  # 限制长度避免 token 过多
            })

        logger.info("[WebSearch] 搜索完成: query='%s', results=%d", query, len(results))

        return json.dumps({
            "query": query,
            "results": results,
            "total": len(results),
        }, ensure_ascii=False)

    except ImportError:
        logger.error("[WebSearch] tavily-python 未安装，请运行: pip install tavily-python")
        return json.dumps({
            "query": query,
            "results": [],
            "total": 0,
            "error": "搜索依赖未安装",
        }, ensure_ascii=False)

    except Exception as e:
        logger.error("[WebSearch] 搜索失败: %s", e)
        return json.dumps({
            "query": query,
            "results": [],
            "total": 0,
            "error": str(e),
        }, ensure_ascii=False)


def format_web_results(search_result_str: str) -> str:
    """
    将搜索结果格式化为 Prompt 可用的文本。

    Args:
        search_result_str: web_search 返回的 JSON 字符串

    Returns:
        格式化后的文本
    """
    try:
        data = json.loads(search_result_str)
        results = data.get("results", [])

        if not results:
            return "暂无互联网搜索结果"

        parts = []
        for i, item in enumerate(results, 1):
            title = item.get("title", "无标题")
            url = item.get("url", "")
            content = item.get("content", "无内容")
            parts.append(f"[Web {i}] {title}\n链接: {url}\n摘要: {content}")

        return "\n\n".join(parts)

    except (json.JSONDecodeError, KeyError):
        return "搜索结果解析失败"
