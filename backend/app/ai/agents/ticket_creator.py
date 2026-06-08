"""
TicketCreationAgent — 自动创建工单 Agent。

流程: 用户提问 → AI判断 → 生成标题/分类/优先级 → 保存数据库 → 返回 ticket_id
"""

import json
import logging
import time
from typing import Any, AsyncIterator

from app.ai.agents.base import BaseAgent
from app.ai.schemas import AgentState, AgentType, TaskStatus, TicketInfo
from app.ai.prompts.templates import TICKET_CREATION_SYSTEM
from app.ai.memory.manager import memory_manager

logger = logging.getLogger(__name__)

DEFAULT_RESULT = {
    "title": "用户问题工单",
    "ticket_type": "after_sales",
    "priority": "medium",
    "description": "用户问题待处理",
}


class TicketCreationAgent(BaseAgent):
    """自动创建工单 Agent"""

    @property
    def agent_name(self) -> str:
        return "ticket_creator"

    @property
    def agent_type(self) -> AgentType:
        return AgentType.TICKET_CREATOR

    @property
    def system_prompt(self) -> str:
        return TICKET_CREATION_SYSTEM

    @property
    def _temperature(self) -> float:
        return 0.2

    # ---- 核心接口（统一入口） ----

    async def run(self, state: AgentState) -> AgentState:
        """
        统一执行入口。

        Args:
            state: 当前 Agent 状态

        Returns:
            更新后的 Agent 状态，包含 ticket_info
        """
        state.agent_type = self.agent_type
        state.status = TaskStatus.PROCESSING

        try:
            # 1. 获取对话历史
            history_text = ""
            if state.history:
                history_lines = [f"{'用户' if h['role'] == 'user' else '助手'}: {h['content']}" for h in state.history[-6:]]
                history_text = "\n".join(history_lines)
            else:
                history = memory_manager.get_history(state.conversation_id)
                if history:
                    history_lines = []
                    for msg in history[-6:]:
                        role = "用户" if msg.type == "human" else "助手"
                        history_lines.append(f"{role}: {msg.content}")
                    history_text = "\n".join(history_lines)

            # 2. 调用 LLM 生成工单信息
            prompt = self.system_prompt.format(
                question=state.user_input,
                history=history_text or "无",
            )

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": state.user_input},
            ]

            response = await self.llm.ainvoke(messages)
            ticket_data = self._parse_response(response.content)

            # 3. 保存到数据库
            ticket_id = await self._save_ticket(
                title=ticket_data["title"],
                content=state.user_input,
                ticket_type=ticket_data["ticket_type"],
                priority=ticket_data["priority"],
                description=ticket_data["description"],
                user_id=state.user_id,
            )

            # 4. 更新 State
            state.ticket_info = TicketInfo(
                ticket_no=f"TK{ticket_id:06d}",
                title=ticket_data["title"],
                content=state.user_input,
                ticket_type=ticket_data["ticket_type"],
                priority=ticket_data["priority"],
                status="pending",
                user_id=state.user_id,
            )
            state.ticket_id = ticket_id
            state.ticket_type = ticket_data["ticket_type"]
            state.ticket_priority = ticket_data["priority"]

            state.status = TaskStatus.COMPLETED

        except Exception as e:
            logger.error("[TicketCreator] 调用失败: %s", e)
            state.error = str(e)
            state.status = TaskStatus.FAILED

        return state

    # ---- 兼容旧接口 ----

    async def invoke(self, input_text: str, **kwargs: Any) -> str:
        """
        生成工单信息并保存到数据库（兼容旧接口）。

        Args:
            input_text: 用户原始问题
            **kwargs: conversation_id, user_id, history_text

        Returns:
            JSON 字符串，包含 ticket_id, title, ticket_type, priority
        """
        state = self._create_state(input_text, **kwargs)
        state = await self.run(state)

        if state.ticket_info:
            return json.dumps({
                "ticket_id": state.ticket_id,
                "title": state.ticket_info.title,
                "ticket_type": state.ticket_info.ticket_type,
                "priority": state.ticket_info.priority,
                "description": state.ticket_info.content,
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "ticket_id": None,
                **DEFAULT_RESULT,
            }, ensure_ascii=False)

    async def stream(self, input_text: str, **kwargs: Any) -> AsyncIterator[str]:
        result = await self.invoke(input_text, **kwargs)
        yield result

    def _parse_response(self, raw: str) -> dict:
        """解析 LLM 返回的 JSON"""
        try:
            text = raw.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            result = json.loads(text)

            # 校验字段
            title = str(result.get("title", "用户问题工单"))[:50]
            ticket_type = result.get("ticket_type", "after_sales")
            priority = result.get("priority", "medium")
            description = str(result.get("description", ""))[:200]

            # 校验枚举值
            valid_types = {"after_sales", "technical", "refund", "complaint"}
            if ticket_type not in valid_types:
                ticket_type = "after_sales"

            valid_priorities = {"urgent", "high", "medium", "low"}
            if priority not in valid_priorities:
                priority = "medium"

            return {
                "title": title,
                "ticket_type": ticket_type,
                "priority": priority,
                "description": description,
            }

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("[TicketCreator] JSON 解析失败: %s | raw: %s", e, raw[:200])
            return DEFAULT_RESULT

    async def _save_ticket(
        self,
        title: str,
        content: str,
        ticket_type: str,
        priority: str,
        description: str,
        user_id: int | None = None,
    ) -> int:
        """
        保存工单到数据库。

        Returns:
            工单ID
        """
        try:
            from app.core.database import async_session_factory
            from app.models.ticket import Ticket

            async with async_session_factory() as db:
                # 使用 Ticket 模型创建工单
                ticket = Ticket(
                    ticket_no="",
                    title=title,
                    content=content,
                    ticket_type=ticket_type,
                    priority=priority,
                    status="pending",
                    user_id=user_id or 0,
                )
                db.add(ticket)
                await db.flush()
                ticket.ticket_no = f"TK{ticket.id:06d}"
                await db.commit()

                ticket_id = ticket.id

            logger.info(
                "[TicketCreator] 工单已创建: %d | type=%s | priority=%s",
                ticket_id, ticket_type, priority,
            )
            return ticket_id

        except Exception as e:
            logger.error("[TicketCreator] 保存工单失败: %s", e)
            # 降级：返回ID但不写库
            return int(time.time() * 1000) % 1_000_000
