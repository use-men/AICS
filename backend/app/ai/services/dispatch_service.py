"""
DispatchService — 自动派单服务。

工单创建后自动触发:
    1. 识别工单类型
    2. 匹配客服技能
    3. 检查在线状态
    4. 选择工单最少的客服
    5. 自动分配
"""

import logging
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_service import CustomerService
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)

# ---- 工单类型 → 技能映射 ----

TICKET_TYPE_SKILL_MAP = {
    "after_sales": ["after_sales", "all"],      # 售后咨询
    "technical": ["technical", "all"],            # 技术支持
    "refund": ["refund", "all"],                  # 退款申请
    "complaint": ["complaint", "all"],            # 投诉建议
}

TICKET_TYPE_NAMES = {
    "after_sales": "售后咨询",
    "technical": "技术支持",
    "refund": "退款申请",
    "complaint": "投诉建议",
}


class DispatchService:
    """
    自动派单服务。

    派单规则:
        1. 技能匹配（必须）
        2. 在线状态（online > busy > offline）
        3. 工单最少（负载最低优先）
    """

    async def auto_dispatch(
        self,
        ticket_id: int,
        ticket_type: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        自动派单。

        Args:
            ticket_id: 工单ID
            ticket_type: 工单类型
            db: 数据库会话

        Returns:
            {"service_id": int, "service_name": str} 或 {"error": str}
        """
        # 1. 获取所需技能
        required_skills = TICKET_TYPE_SKILL_MAP.get(ticket_type, ["all"])

        # 2. 查询可用客服（在线且活跃）
        result = await db.execute(
            select(CustomerService).where(
                CustomerService.is_active == True,
                CustomerService.online_status.in_(["online", "busy"]),
            )
        )
        agents = result.scalars().all()

        if not agents:
            logger.warning("[Dispatch] 无可用客服，工单 %d 等待手动分配", ticket_id)
            return {"error": "当前无可用客服"}

        # 3. 按规则筛选和排序
        scored_agents = []
        for agent in agents:
            score = self._calculate_score(agent, required_skills)
            scored_agents.append((agent, score))

        # 4. 按分数降序排序（分数越高越优先）
        scored_agents.sort(key=lambda x: x[1], reverse=True)

        # 5. 选择最佳客服
        best_agent, best_score = scored_agents[0]

        # 6. 更新工单
        ticket = await db.get(Ticket, ticket_id)
        if ticket:
            ticket.service_id = best_agent.id
            ticket.status = "assigned"
            await db.commit()

        # 7. 更新客服工单计数
        best_agent.current_ticket_count += 1
        await db.commit()

        logger.info(
            "[Dispatch] 工单 %d 分配给 %s (ID=%d, score=%.3f) | 类型=%s",
            ticket_id, best_agent.name, best_agent.id, best_score,
            TICKET_TYPE_NAMES.get(ticket_type, ticket_type),
        )

        return {
            "service_id": best_agent.id,
            "service_name": best_agent.name,
            "skill_type": best_agent.skill_type,
            "score": best_score,
        }

    def _calculate_score(
        self,
        agent: CustomerService,
        required_skills: list[str],
    ) -> float:
        """
        计算客服评分。

        评分规则:
            1. 技能匹配: 匹配=1.0, 不匹配=0.3
            2. 在线状态: online=1.0, busy=0.6
            3. 负载率: 越低分越高 (1.0 - load_ratio)

        公式:
            score = 技能匹配 * 50 + 在线状态 * 30 + (1-负载率) * 20
        """
        # 技能匹配 (50分)
        skill_score = 100 if agent.skill_type in required_skills else 30

        # 在线状态 (30分)
        if agent.online_status == "online":
            status_score = 100
        elif agent.online_status == "busy":
            status_score = 60
        else:
            status_score = 0

        # 负载率 (20分) — 工单越少分越高
        load_score = (1.0 - agent.load_ratio) * 100

        # 综合评分 (0-100)
        total_score = skill_score * 0.5 + status_score * 0.3 + load_score * 0.2

        return round(total_score, 2)

    async def get_available_agents(self, db: AsyncSession) -> list[dict]:
        """获取所有可用客服"""
        result = await db.execute(
            select(CustomerService).where(
                CustomerService.is_active == True,
                CustomerService.online_status.in_(["online", "busy"]),
            ).order_by(CustomerService.current_ticket_count)
        )
        agents = result.scalars().all()

        return [
            {
                "id": agent.id,
                "name": agent.name,
                "skill_type": agent.skill_type,
                "current_ticket_count": agent.current_ticket_count,
                "max_ticket_count": agent.max_ticket_count,
                "online_status": agent.online_status,
                "load_ratio": agent.load_ratio,
            }
            for agent in agents
        ]

    async def get_dispatch_stats(self, db: AsyncSession) -> dict:
        """获取派单统计"""
        # 总客服数
        total = (await db.execute(select(func.count(CustomerService.id)))).scalar() or 0

        # 在线客服数
        online = (await db.execute(
            select(func.count(CustomerService.id)).where(
                CustomerService.online_status == "online"
            )
        )).scalar() or 0

        # 忙碌客服数
        busy = (await db.execute(
            select(func.count(CustomerService.id)).where(
                CustomerService.online_status == "busy"
            )
        )).scalar() or 0

        # 离线客服数
        offline = total - online - busy

        # 各技能客服数
        skill_result = await db.execute(
            select(CustomerService.skill_type, func.count(CustomerService.id))
            .where(CustomerService.is_active == True)
            .group_by(CustomerService.skill_type)
        )
        by_skill = {row[0]: row[1] for row in skill_result.all()}

        return {
            "total": total,
            "online": online,
            "busy": busy,
            "offline": offline,
            "by_skill": by_skill,
        }


# ---- 全局单例 ----

dispatch_service = DispatchService()
