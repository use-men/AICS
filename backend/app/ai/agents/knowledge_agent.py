"""
KnowledgeAgent — RAG 知识库问答 Agent。

流程: 用户提问 → Embedding → FAISS检索 → 召回TopK → DeepSeek生成答案
"""

import json
import logging
from typing import Any, AsyncIterator

from app.ai.agents.base import BaseAgent
from app.ai.prompts.templates import KNOWLEDGE_QA_SYSTEM
from app.ai.services.vector_store import vector_store
from app.ai.memory.manager import memory_manager

logger = logging.getLogger(__name__)

DEFAULT_RESULT = {
    "answer": "抱歉，知识库中暂无相关内容，请联系人工客服。",
    "sources": [],
}


class KnowledgeAgent(BaseAgent):
    """RAG 知识库问答 Agent"""

    @property
    def agent_name(self) -> str:
        return "knowledge_agent"

    @property
    def system_prompt(self) -> str:
        return KNOWLEDGE_QA_SYSTEM

    @property
    def _temperature(self) -> float:
        return 0.3

    async def invoke(self, input_text: str, **kwargs: Any) -> str:
        """
        知识库问答。

        Args:
            input_text: 用户问题
            **kwargs: conversation_id, top_k

        Returns:
            JSON 字符串，包含 answer 和 sources
        """
        conversation_id = kwargs.get("conversation_id", "default")
        top_k = kwargs.get("top_k", 3)

        try:
            # 1. 检索相关文档
            search_results = vector_store.search(input_text, top_k=top_k)

            # 2. 构建上下文
            context_parts = []
            sources = []
            for i, result in enumerate(search_results, 1):
                context_parts.append(f"[{i}] {result['content']}")
                sources.append({
                    "content": result["content"][:200],
                    "score": round(result["score"], 3),
                })

            context = "\n\n".join(context_parts) if context_parts else "暂无相关知识库内容"

            # 3. 获取对话历史
            history = memory_manager.get_history(conversation_id)
            history_text = ""
            if history:
                history_lines = []
                for msg in history[-6:]:  # 最近3轮
                    role = "用户" if msg.type == "human" else "助手"
                    history_lines.append(f"{role}: {msg.content}")
                history_text = "\n".join(history_lines)

            # 4. 构建 Prompt
            prompt = self.system_prompt.format(
                context=context,
                history=history_text,
                question=input_text,
            )

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": input_text},
            ]

            # 5. 调用 LLM
            response = await self.llm.ainvoke(messages)

            return json.dumps({
                "answer": response.content,
                "sources": sources,
            }, ensure_ascii=False)

        except Exception as e:
            logger.error("[KnowledgeAgent] 调用失败: %s", e)
            return json.dumps(DEFAULT_RESULT, ensure_ascii=False)

    async def stream(self, input_text: str, **kwargs: Any) -> AsyncIterator[str]:
        """流式问答"""
        conversation_id = kwargs.get("conversation_id", "default")
        top_k = kwargs.get("top_k", 3)

        try:
            # 1. 检索
            search_results = vector_store.search(input_text, top_k=top_k)

            context_parts = [r["content"] for r in search_results]
            context = "\n\n".join(context_parts) if context_parts else "暂无相关知识库内容"

            # 2. 获取历史
            history = memory_manager.get_history(conversation_id)
            history_text = ""
            if history:
                history_lines = []
                for msg in history[-6:]:
                    role = "用户" if msg.type == "human" else "助手"
                    history_lines.append(f"{role}: {msg.content}")
                history_text = "\n".join(history_lines)

            # 3. 构建 Prompt
            prompt = self.system_prompt.format(
                context=context,
                history=history_text,
                question=input_text,
            )

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": input_text},
            ]

            # 4. 流式调用
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            logger.error("[KnowledgeAgent] 流式调用失败: %s", e)
            yield "抱歉，知识库服务暂时不可用，请稍后再试。"
