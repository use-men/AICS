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
from app.ai.schemas import AgentState, AgentType, TaskStatus, TransferReason
from app.ai.services.knowledge_service import knowledge_service
from app.ai.memory.manager import memory_manager
from app.ai.tools.web_search import web_search, format_web_results

logger = logging.getLogger(__name__)

TRANSFER_MARKER = "[TRANSFER_TO_HUMAN]"

# ---- 转人工关键词 ----
TRANSFER_KEYWORDS = [
    "转人工", "找人工", "人工客服", "人工服务", "转接人工",
    "真人", "找客服", "转客服",
]

SYSTEM_PROMPT = """你是 SmartDesk 智能客服平台的 AI 客服助手。

## 任务
基于知识库检索结果、互联网搜索结果和对话历史，为用户提供准确、友好的回答。

## 规则
1. 优先基于【知识库内容】回答，不要编造信息
2. 如果知识库没有相关内容，参考【互联网搜索结果】
3. 回答要友好、专业、简洁，使用中文
4. 可以结合对话历史进行多轮对话
5. 引用知识库内容时，标注来源编号如 [1][2]
6. 引用互联网搜索结果时，标注"来源：互联网"并提供链接

## 转人工判断
如果遇到以下情况，在回答末尾加上 [TRANSFER_TO_HUMAN] 标记：
- 知识库和互联网搜索都无法回答用户问题
- 用户明确要求转人工（如说"转人工"、"找人工客服"）
- 用户情绪激动或不满（如说"投诉"、"不满"、"太差了"）
- 经过2轮对话仍无法解决用户问题

## 知识库检索结果
{context}

## 互联网搜索结果
{web_search_results}

## 对话历史
{history}
"""

DEEP_THINKING_PROMPT = """你是 SmartDesk 智能客服平台的 AI 客服助手，当前处于【深度思考模式】。

## 任务
基于知识库检索结果、互联网搜索结果和对话历史，进行深入分析后为用户提供准确、全面的回答。

## 思考流程
请按照以下步骤进行深度思考：

**第一步：问题分析**
- 分析用户问题的核心意图
- 识别问题涉及的关键知识点
- 判断问题的复杂程度

**第二步：知识库匹配**
- 评估检索到的知识库内容与问题的相关性
- 找出最匹配的知识片段
- 标注知识库中的关键信息

**第三步：互联网搜索补充**
- 如果知识库内容不足，参考互联网搜索结果
- 评估搜索结果的可信度和相关性
- 提取关键信息作为补充

**第四步：推理与整合**
- 综合知识库内容、互联网搜索结果和对话历史
- 分析可能的解决方案
- 考虑各种因素和限制条件

**第五步：生成回答**
- 基于以上分析，生成准确、完整的回答
- 引用知识库来源编号如 [1][2]
- 引用互联网搜索结果时标注"来源：互联网"
- 如有需要，给出具体的操作建议

## 转人工判断
如果遇到以下情况，在回答末尾加上 [TRANSFER_TO_HUMAN] 标记：
- 知识库和互联网搜索都无法回答用户问题
- 用户明确要求转人工（如说"转人工"、"找人工客服"）
- 用户情绪激动或不满（如说"投诉"、"不满"、"太差了"）
- 经过2轮对话仍无法解决用户问题

## 知识库检索结果
{context}

## 互联网搜索结果
{web_search_results}

## 对话历史
{history}
"""


class CustomerServiceAgent(BaseAgent):
    """用户端 AI 客服 Agent"""

    @property
    def agent_name(self) -> str:
        return "cs_agent"

    @property
    def agent_type(self) -> AgentType:
        return AgentType.CUSTOMER_SERVICE

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

    # ---- 核心接口（统一入口） ----

    async def run(self, state: AgentState) -> AgentState:
        """
        统一执行入口。

        Args:
            state: 当前 Agent 状态

        Returns:
            更新后的 Agent 状态
        """
        state.agent_type = self.agent_type
        state.status = TaskStatus.PROCESSING

        try:
            # 0. 检测用户是否主动要求转人工
            if self._check_transfer_keywords(state.user_input):
                state.need_human = True
                state.transfer_reason = TransferReason.USER_REQUEST
                state.answer = "好的，正在为您转接人工客服，请稍候..."
                state.status = TaskStatus.TRANSFERRED
                memory_manager.add_message(state.conversation_id, "user", state.user_input)
                memory_manager.add_message(state.conversation_id, "assistant", state.answer)
                return state

            # 1. 检索知识库
            search_results = await knowledge_service.search(state.user_input, top_k=5)
            state.set_knowledge_results(search_results)

            # 2. 如果知识库置信度低，触发联网搜索
            if state.low_confidence and ai_settings.WEB_SEARCH_ENABLED and ai_settings.TAVILY_API_KEY:
                try:
                    raw_results = await web_search(state.user_input)
                    if isinstance(raw_results, str):
                        raw_results = json.loads(raw_results)
                    state.set_web_search_results(raw_results.get("results", []))
                except Exception as e:
                    logger.warning("[CSAgent] 联网搜索失败: %s", e)

            # 3. 获取对话历史
            history = memory_manager.get_history(state.conversation_id)
            if history:
                for msg in history[-6:]:
                    role = "user" if msg.type == "human" else "assistant"
                    state.add_history(role, msg.content)

            # 4. 构建 Prompt
            history_text = "\n".join([f"{'用户' if h['role'] == 'user' else '助手'}: {h['content']}" for h in state.history])
            system_msg = self.system_prompt.format(
                context=state.knowledge_context,
                web_search_results=state.web_search_context,
                history=history_text or "无",
            )

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": state.user_input},
            ]

            # 5. 调用 DeepSeek
            response = await self.llm.ainvoke(messages)
            state.answer = response.content

            # 6. 判断是否需要转人工
            if TRANSFER_MARKER in state.answer or state.low_confidence:
                state.need_human = True
                state.transfer_reason = TransferReason.LOW_CONFIDENCE if state.low_confidence else TransferReason.LLM_JUDGMENT
            state.answer = state.answer.replace(TRANSFER_MARKER, "").strip()

            # 7. 保存对话记忆
            memory_manager.add_message(state.conversation_id, "user", state.user_input)
            memory_manager.add_message(state.conversation_id, "assistant", state.answer)

            state.status = TaskStatus.COMPLETED

        except Exception as e:
            logger.error("[CSAgent] 调用失败: %s", e)
            state.error = str(e)
            state.status = TaskStatus.FAILED
            state.need_human = True
            state.transfer_reason = TransferReason.ERROR
            state.answer = "抱歉，AI客服暂时不可用，请稍后再试。"

        return state

    # ---- 兼容旧接口 ----

    async def invoke(self, input_text: str, **kwargs: Any) -> str:
        """
        AI 客服对话（非流式，兼容旧接口）。

        Args:
            input_text: 用户问题
            **kwargs: conversation_id, user_id

        Returns:
            JSON 字符串，包含 answer, need_human, sources, transfer_reason
        """
        state = self._create_state(input_text, **kwargs)
        state = await self.run(state)

        return json.dumps({
            "answer": state.answer,
            "need_human": state.need_human,
            "sources": [
                {
                    "question": sr.question,
                    "answer": sr.answer[:200],
                    "score": round(sr.score, 3),
                }
                for sr in state.knowledge_results
            ],
            "transfer_reason": state.transfer_reason.value if state.transfer_reason else None,
        }, ensure_ascii=False)

    async def stream(self, input_text: str, **kwargs: Any) -> AsyncIterator[str]:
        """
        流式 AI 客服（兼容旧接口）。

        Yields:
            文本片段（SSE 格式）
        """
        conversation_id = kwargs.get("conversation_id", "default")
        deep_thinking = kwargs.get("deep_thinking", False)

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

            # 4.1 如果知识库置信度低，触发联网搜索
            web_search_results = "暂无互联网搜索结果"
            logger.info("[CSAgent Stream] 置信度检查: low_confidence=%s, WEB_SEARCH_ENABLED=%s, TAVILY_API_KEY=%s",
                       low_confidence, ai_settings.WEB_SEARCH_ENABLED,
                       "已配置" if ai_settings.TAVILY_API_KEY else "未配置")
            if low_confidence and ai_settings.WEB_SEARCH_ENABLED and ai_settings.TAVILY_API_KEY:
                yield json.dumps({"type": "status", "content": "知识库未找到相关内容，正在搜索互联网..."}, ensure_ascii=False)
                try:
                    logger.info("[CSAgent Stream] 触发联网搜索: %s", input_text)
                    raw_results = await web_search(input_text)
                    web_search_results = format_web_results(raw_results)
                    logger.info("[CSAgent Stream] 联网搜索完成")
                    yield json.dumps({"type": "web_search", "content": "互联网搜索完成"}, ensure_ascii=False)
                except Exception as e:
                    logger.warning("[CSAgent] 联网搜索失败: %s", e)

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

            # 6. 构建 Prompt（根据是否深度思考选择不同 prompt）
            prompt_template = DEEP_THINKING_PROMPT if deep_thinking else self.system_prompt
            system_msg = prompt_template.format(
                context=context,
                web_search_results=web_search_results,
                history=history_text or "无",
            )

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": input_text},
            ]

            # 7. 发送开始生成状态
            if deep_thinking:
                yield json.dumps({"type": "status", "content": "🧠 深度思考中..."}, ensure_ascii=False)
            else:
                yield json.dumps({"type": "status", "content": "正在生成回答..."}, ensure_ascii=False)

            # 8. 流式调用 DeepSeek
            full_answer = ""
            thinking_content = ""
            in_thinking = False

            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    text = chunk.content
                    full_answer += text

                    # 深度思考模式：解析 <think> 标签
                    if deep_thinking:
                        # 检测思考开始
                        if "<think>" in text and not in_thinking:
                            in_thinking = True
                            think_start = text.index("<think>") + 6
                            think_text = text[think_start:]
                            if think_text:
                                thinking_content += think_text
                                yield json.dumps({"type": "thinking", "content": think_text}, ensure_ascii=False)
                            continue

                        # 检测思考结束
                        if "</think>" in text and in_thinking:
                            in_thinking = False
                            think_end = text.index("</think>")
                            think_text = text[:think_end]
                            if think_text:
                                thinking_content += think_text
                                yield json.dumps({"type": "thinking", "content": think_text}, ensure_ascii=False)
                            # 输出 </think> 之后的内容作为正式回答
                            after_think = text[think_end + 8:]
                            if after_think:
                                yield json.dumps({"type": "delta", "content": after_think}, ensure_ascii=False)
                            continue

                        # 在思考中
                        if in_thinking:
                            thinking_content += text
                            yield json.dumps({"type": "thinking", "content": text}, ensure_ascii=False)
                            continue

                    # 正常输出
                    yield json.dumps({"type": "delta", "content": text}, ensure_ascii=False)

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
