"""
DispatchAgent — 智能工单调度 Agent。

根据工单类型、优先级、客服技能、负载情况，自动分配最合适的客服。
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_service import CustomerService

logger = logging.getLogger(__name__)

# ---- 技能类型映射 ----

SKILL_MAP = {
    "after_sales": ["after_sales", "all"],
    "technical": ["technical", "all"],
    "refund": ["refund", "all"],
    "complaint": ["complaint", "all"],
}

# ---- 优先级权重 ----

PRIORITY_WEIGHT = {
    "urgent": 1.5,
    "high": 1.2,
    "medium": 1.0,
    "low": 0.8,
}


class DispatchAgent:
    """
    智能调度 Agent — 加权评分算法。

    评分维度:
        1. 技能匹配度 (40%)
        2. 负载率 (30%) — 负载越低分越高
        3. 在线状态 (20%)
        4. 优先级加成 (10%)

    公式:
        score = skill_score * 0.4 + load_score * 0.3 + online_score * 0.2 + priority_bonus * 0.1
    """

    # 权重配置
    WEIGHT_SKILL = 0.4
    WEIGHT_LOAD = 0.3
    WEIGHT_ONLINE = 0.2
    WEIGHT_PRIORITY = 0.1

    async def dispatch(
        self,
        ticket_type: str,
        priority: str,
        db: AsyncSession,
    ) -> CustomerService | None:
        """
        分配最合适的客服。

        Args:
            ticket_type: 工单类型 (after_sales/technical/refund/complaint)
            priority: 优先级 (urgent/high/medium/low)
            db: 数据库会话

        Returns:
            最佳客服，无可用客服返回 None
        """
        # 1. 查询所有在线且活跃的客服
        result = await db.execute(
            select(CustomerService).where(
                CustomerService.is_active == True,
                CustomerService.online_status.in_(["online", "busy"]),
            )
        )
        agents = result.scalars().all()

        if not agents:
            logger.warning("[Dispatch] 无可用客服")
            return None

        # 2. 评分
        scored = []
        required_skills = SKILL_MAP.get(ticket_type, ["all"])

        for agent in agents:
            score = self._calculate_score(agent, required_skills, priority)
            scored.append((agent, score))

        # 3. 按分数降序排序
        scored.sort(key=lambda x: x[1], reverse=True)

        # 4. 返回最佳客服
        best_agent, best_score = scored[0]
        logger.info(
            "[Dispatch] 分配客服: %s (score=%.3f) | 工单类型=%s 优先级=%s",
            best_agent.name, best_score, ticket_type, priority,
        )

        return best_agent

    def _calculate_score(
        self,
        agent: CustomerService,
        required_skills: list[str],
        priority: str,
    ) -> float:
        """
        计算客服评分。

        Args:
            agent: 客服对象
            required_skills: 所需技能列表
            priority: 工单优先级

        Returns:
            综合评分 0.0 ~ 1.0
        """
        # 1. 技能匹配度 (0 or 1)
        skill_score = 1.0 if agent.skill_type in required_skills else 0.3

        # 2. 负载率得分 (负载越低分越高)
        load_score = 1.0 - agent.load_ratio

        # 3. 在线状态得分
        if agent.online_status == "online":
            online_score = 1.0
        elif agent.online_status == "busy":
            online_score = 0.6
        else:
            online_score = 0.0

        # 4. 优先级加成 (busy 状态下高优先级工单可获得加成)
        priority_weight = PRIORITY_WEIGHT.get(priority, 1.0)
        priority_bonus = 1.0
        if agent.online_status == "busy" and priority_weight >= 1.2:
            priority_bonus = 0.8  # busy 状态略微降低，但仍可被选中

        # 综合评分
        score = (
            skill_score * self.WEIGHT_SKILL
            + load_score * self.WEIGHT_LOAD
            + online_score * self.WEIGHT_ONLINE
            + priority_bonus * self.WEIGHT_PRIORITY
        ) * priority_weight

        return round(score, 4)


# ---- 全局单例 ----

dispatch_agent = DispatchAgent()
