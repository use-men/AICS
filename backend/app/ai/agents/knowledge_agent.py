"""
KnowledgeAgent — RAG 知识库问答 Agent。

流程: 用户提问 → Embedding → FAISS检索 → 召回TopK → DeepSeek生成答案
"""

import json
import logging
from typing import Any, AsyncIterator

from app.ai.agents.base import BaseAgent
from app.ai.schemas import AgentState, AgentType, TaskStatus, TransferReason
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
    def agent_type(self) -> AgentType:
        return AgentType.KNOWLEDGE

    @property
    def system_prompt(self) -> str:
        return KNOWLEDGE_QA_SYSTEM

    @property
    def _temperature(self) -> float:
        return 0.3

    # ---- 核心接口（统一入口） ----

    async def run(self, state: AgentState) -> AgentState:
        """
        统一执行入口。

        Args:
            state: 当前 Agent 状态

        Returns:
            更新后的 Agent 状态，包含 answer 和 knowledge_results
        """
        state.agent_type = self.agent_type
        state.status = TaskStatus.PROCESSING

        try:
            # 1. 检索相关文档
            top_k = state.metadata.get("top_k", 3)
            search_results = vector_store.search(state.user_input, top_k=top_k)
            state.set_knowledge_results(search_results)

            # 2. 获取对话历史
            if state.history:
                history_text = "\n".join([f"{'用户' if h['role'] == 'user' else '助手'}: {h['content']}" for h in state.history[-6:]])
            else:
                history = memory_manager.get_history(state.conversation_id)
                history_text = ""
                if history:
                    history_lines = []
                    for msg in history[-6:]:
                        role = "用户" if msg.type == "human" else "助手"
                        history_lines.append(f"{role}: {msg.content}")
                    history_text = "\n".join(history_lines)

            # 3. 构建 Prompt
            prompt = self.system_prompt.format(
                context=state.knowledge_context,
                history=history_text,
                question=state.user_input,
            )

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": state.user_input},
            ]

            # 4. 调用 LLM
            response = await self.llm.ainvoke(messages)
            state.answer = response.content

            # 5. 检查是否需要转人工
            TRANSFER_MARKER = "[TRANSFER_TO_HUMAN]"
            if TRANSFER_MARKER in state.answer:
                state.need_human = True
                state.transfer_reason = TransferReason.LLM_JUDGMENT
                state.answer = state.answer.replace(TRANSFER_MARKER, "").strip()
            # 注意：不再因为 low_confidence 就触发转人工
            # 只有用户明确表达需要人工时才触发

            state.status = TaskStatus.COMPLETED

        except Exception as e:
            logger.error("[KnowledgeAgent] 调用失败: %s", e)
            state.error = str(e)
            state.status = TaskStatus.FAILED
            state.answer = "抱歉，知识库服务暂时不可用，请稍后再试。"

        return state

    # ---- 兼容旧接口 ----

    async def invoke(self, input_text: str, **kwargs: Any) -> str:
        """
        知识库问答（兼容旧接口）。

        Args:
            input_text: 用户问题
            **kwargs: conversation_id, top_k

        Returns:
            JSON 字符串，包含 answer 和 sources
        """
        state = self._create_state(input_text, **kwargs)
        state.metadata["top_k"] = kwargs.get("top_k", 3)
        state = await self.run(state)

        return json.dumps({
            "answer": state.answer,
            "sources": [
                {
                    "content": sr.answer[:200],
                    "score": round(sr.score, 3),
                }
                for sr in state.knowledge_results
            ],
        }, ensure_ascii=False)

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
