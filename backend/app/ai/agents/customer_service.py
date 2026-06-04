"""
CustomerServiceAgent — 用户端 AI 客服 Agent。

流程:
    用户提问 → 知识库检索 → 获取知识片段 → 构造Prompt → 调用DeepSeek → 返回答案

支持:
    - 多轮对话
    - 历史上下文
    - 流式输出
    - 置信度检测（低置信度自动转人工）
    - 用户主动要求转人工
"""

import json
import logging
from typing import Any, AsyncIterator

from app.ai.agents.base import BaseAgent
from app.ai.config import ai_settings
from app.ai.services.knowledge_service import knowledge_service
from app.ai.memory.manager import memory_manager

logger = logging.getLogger(__name__)

TRANSFER_MARKER = "[TRANSFER_TO_HUMAN]"

# ---- 转人工关键词 ----
TRANSFER_KEYWORDS = [
    "转人工", "找人工", "人工客服", "人工服务", "转接人工",
    "真人", "找客服", "转客服",
]

SYSTEM_PROMPT = """你是 SmartDesk 智能客服平台的 AI 客服助手。

## 任务
基于知识库检索结果和对话历史，为用户提供准确、友好的回答。

## 规则
1. 优先基于【知识库内容】回答，不要编造信息
2. 如果知识库没有相关内容，如实告知并建议联系人工客服
3. 回答要友好、专业、简洁，使用中文
4. 可以结合对话历史进行多轮对话
5. 引用知识库内容时，标注来源编号如 [1][2]

## 转人工判断
如果遇到以下情况，在回答末尾加上 [TRANSFER_TO_HUMAN] 标记：
- 知识库无法回答用户问题（检索结果为空或不相关）
- 用户明确要求转人工（如说"转人工"、"找人工客服"）
- 用户情绪激动或不满（如说"投诉"、"不满"、"太差了"）
- 经过2轮对话仍无法解决用户问题

## 知识库检索结果
{context}

## 对话历史
{history}
"""


class CustomerServiceAgent(BaseAgent):
    """用户端 AI 客服 Agent"""

    @property
    def agent_name(self) -> str:
        return "cs_agent"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def _temperature(self) -> float:
        return 0.3

    # ---- 辅助方法 ----

    @staticmethod
    def _check_transfer_keywords(text: str) -> bool:
        """检测用户是否主动要求转人工"""
        return any(kw in text for kw in TRANSFER_KEYWORDS)

    @staticmethod
    def _check_confidence(search_results: list[dict]) -> bool:
        """
        根据知识库检索结果的最高置信度判断是否需要转人工。

        Returns:
            True = 需要转人工（置信度低）
        """
        if not search_results:
            return True
        max_score = max(r.get("score", 0) for r in search_results)
        return max_score < ai_settings.CONFIDENCE_THRESHOLD

    async def invoke(self, input_text: str, **kwargs: Any) -> str:
        """
        AI 客服对话（非流式）。

        Args:
            input_text: 用户问题
            **kwargs: conversation_id, user_id

        Returns:
            JSON 字符串，包含 answer, need_human, sources, transfer_reason
        """
        conversation_id = kwargs.get("conversation_id", "default")
        user_id = kwargs.get("user_id")

        try:
            # 0. 检测用户是否主动要求转人工
            if self._check_transfer_keywords(input_text):
                # 保存对话记忆
                memory_manager.add_message(conversation_id, "user", input_text)
                memory_manager.add_message(conversation_id, "assistant", "好的，正在为您转接人工客服，请稍候...")
                return json.dumps({
                    "answer": "好的，正在为您转接人工客服，请稍候...",
                    "need_human": True,
                    "sources": [],
                    "transfer_reason": "user_request",
                }, ensure_ascii=False)

            # 1. 检索知识库
            search_results = await knowledge_service.search(input_text, top_k=5)

            # 2. 检测置信度
            low_confidence = self._check_confidence(search_results)

            # 3. 构建知识上下文
            context_parts = []
            sources = []
            for i, result in enumerate(search_results, 1):
                meta = result.get("metadata", {})
                question = meta.get("question", "")
                answer = meta.get("answer", "")
                context_parts.append(f"[{i}] 问题: {question}\n回答: {answer}")
                sources.append({
                    "question": question,
                    "answer": answer[:200],
                    "score": round(result.get("score", 0), 3),
                })

            context = "\n\n".join(context_parts) if context_parts else "暂无相关知识库内容"

            # 4. 获取对话历史
            history = memory_manager.get_history(conversation_id)
            history_text = ""
            if history:
                history_lines = []
                for msg in history[-6:]:
                    role = "用户" if msg.type == "human" else "助手"
                    history_lines.append(f"{role}: {msg.content}")
                history_text = "\n".join(history_lines)

            # 5. 构建 Prompt
            system_msg = self.system_prompt.format(
                context=context,
                history=history_text or "无",
            )

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": input_text},
            ]

            # 6. 调用 DeepSeek
            response = await self.llm.ainvoke(messages)
            answer = response.content

            # 7. 判断是否需要转人工
            need_human = TRANSFER_MARKER in answer or low_confidence
            answer = answer.replace(TRANSFER_MARKER, "").strip()

            # 8. 确定转人工原因
            transfer_reason = None
            if need_human:
                if low_confidence:
                    transfer_reason = "low_confidence"
                elif TRANSFER_MARKER in answer:
                    transfer_reason = "llm_judgment"

            # 9. 保存对话记忆
            memory_manager.add_message(conversation_id, "user", input_text)
            memory_manager.add_message(conversation_id, "assistant", answer)

            return json.dumps({
                "answer": answer,
                "need_human": need_human,
                "sources": sources,
                "transfer_reason": transfer_reason,
            }, ensure_ascii=False)

        except Exception as e:
            logger.error("[CSAgent] 调用失败: %s", e)
            return json.dumps({
                "answer": "抱歉，AI客服暂时不可用，请稍后再试。",
                "need_human": True,
                "sources": [],
                "transfer_reason": "error",
            }, ensure_ascii=False)

    async def stream(self, input_text: str, **kwargs: Any) -> AsyncIterator[str]:
        """
        流式 AI 客服。

        Yields:
            文本片段（SSE 格式）
        """
        conversation_id = kwargs.get("conversation_id", "default")

        try:
            # 0. 检测用户是否主动要求转人工
            if self._check_transfer_keywords(input_text):
                memory_manager.add_message(conversation_id, "user", input_text)
                memory_manager.add_message(conversation_id, "assistant", "好的，正在为您转接人工客服，请稍候...")
                yield json.dumps({
                    "type": "done",
                    "content": "好的，正在为您转接人工客服，请稍候...",
                    "need_human": True,
                    "sources": [],
                    "transfer_reason": "user_request",
                }, ensure_ascii=False)
                return

            # 1. 先发送检索状态
            yield json.dumps({"type": "status", "content": "正在检索知识库..."}, ensure_ascii=False)

            # 2. 检索知识库
            search_results = await knowledge_service.search(input_text, top_k=5)

            # 3. 检测置信度
            low_confidence = self._check_confidence(search_results)

            # 4. 发送检索结果
            sources = []
            context_parts = []
            for i, result in enumerate(search_results, 1):
                meta = result.get("metadata", {})
                question = meta.get("question", "")
                answer = meta.get("answer", "")
                context_parts.append(f"[{i}] 问题: {question}\n回答: {answer}")
                sources.append({
                    "question": question,
                    "answer": answer[:200],
                    "score": round(result.get("score", 0), 3),
                })

            context = "\n\n".join(context_parts) if context_parts else "暂无相关知识库内容"

            yield json.dumps({
                "type": "sources",
                "content": f"找到 {len(sources)} 条相关知识",
                "sources": sources,
            }, ensure_ascii=False)

            # 5. 获取对话历史
            history = memory_manager.get_history(conversation_id)
            history_text = ""
            if history:
                history_lines = []
                for msg in history[-6:]:
                    role = "用户" if msg.type == "human" else "助手"
                    history_lines.append(f"{role}: {msg.content}")
                history_text = "\n".join(history_lines)

            # 6. 构建 Prompt
            system_msg = self.system_prompt.format(
                context=context,
                history=history_text or "无",
            )

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": input_text},
            ]

            # 7. 发送开始生成状态
            yield json.dumps({"type": "status", "content": "正在生成回答..."}, ensure_ascii=False)

            # 8. 流式调用 DeepSeek
            full_answer = ""
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    full_answer += chunk.content
                    yield json.dumps({"type": "delta", "content": chunk.content}, ensure_ascii=False)

            # 9. 判断是否需要转人工
            need_human = TRANSFER_MARKER in full_answer or low_confidence
            full_answer = full_answer.replace(TRANSFER_MARKER, "").strip()

            # 10. 确定转人工原因
            transfer_reason = None
            if need_human:
                if low_confidence:
                    transfer_reason = "low_confidence"
                else:
                    transfer_reason = "llm_judgment"

            # 11. 保存对话记忆
            memory_manager.add_message(conversation_id, "user", input_text)
            memory_manager.add_message(conversation_id, "assistant", full_answer)

            # 12. 发送完成信号
            yield json.dumps({
                "type": "done",
                "content": full_answer,
                "need_human": need_human,
                "sources": sources,
                "transfer_reason": transfer_reason,
            }, ensure_ascii=False)

        except Exception as e:
            logger.error("[CSAgent] 流式调用失败: %s", e)
            yield json.dumps({
                "type": "error",
                "content": "抱歉，AI客服暂时不可用，请稍后再试。",
            }, ensure_ascii=False)


# ---- 全局单例 ----

cs_agent = CustomerServiceAgent()
