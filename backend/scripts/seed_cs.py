"""
种子数据：创建客服人员测试数据。

运行方式：
    cd SmartDesk/backend
    python -m scripts.seed_cs
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import async_session_factory, Base, engine
from app.models.customer_service import CustomerService


CS_AGENTS = [
    {"name": "王芳", "skill_type": "after_sales", "current_ticket_count": 2, "online_status": "online"},
    {"name": "李明", "skill_type": "technical", "current_ticket_count": 5, "online_status": "online"},
    {"name": "赵强", "skill_type": "refund", "current_ticket_count": 1, "online_status": "online"},
    {"name": "陈静", "skill_type": "complaint", "current_ticket_count": 3, "online_status": "online"},
    {"name": "刘伟", "skill_type": "all", "current_ticket_count": 8, "online_status": "online"},
    {"name": "张磊", "skill_type": "technical", "current_ticket_count": 10, "online_status": "busy"},
    {"name": "周敏", "skill_type": "after_sales", "current_ticket_count": 0, "online_status": "offline"},
]


async def seed_cs():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("数据表已创建")

    async with async_session_factory() as db:
        for cs in CS_AGENTS:
            result = await db.execute(
                select(CustomerService).where(CustomerService.name == cs["name"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"  跳过: {cs['name']} (已存在)")
                continue

            agent = CustomerService(
                name=cs["name"],
                skill_type=cs["skill_type"],
                current_ticket_count=cs["current_ticket_count"],
                online_status=cs["online_status"],
            )
            db.add(agent)
            await db.flush()
            print(f"  创建: {cs['name']} ({cs['skill_type']})")

        await db.commit()

    print("\n客服数据初始化完成！")
    print("\n测试调度:")
    print("  POST /api/v1/agent/dispatch")
    print('  {"ticket_type": "refund", "priority": "high"}')


if __name__ == "__main__":
    asyncio.run(seed_cs())
