"""
数据库迁移：为 customer_services 表添加 user_id 字段。

使用方式:
    python scripts/migrate_add_user_id.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine, async_session_factory
from app.models.customer_service import CustomerService
from app.models.user import User
from app.core.database import Base
from sqlalchemy import select


async def migrate():
    """执行迁移"""
    print("正在执行数据库迁移...")

    try:
        # 1. 创建表（如果不存在）
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # 2. 检查是否已有 user_id 列
        async with async_session_factory() as db:
            result = await db.execute(text("PRAGMA table_info(customer_services)"))
            columns = [row[1] for row in result.fetchall()]

            if "user_id" not in columns:
                print("  添加 user_id 列...")
                await db.execute(text("ALTER TABLE customer_services ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                await db.commit()
                print("  ✅ user_id 列已添加")
            else:
                print("  ⏭️  user_id 列已存在")

        # 3. 关联客服到用户账号
        print("\n正在关联客服到用户账号...")
        async with async_session_factory() as db:
            # 查找所有客服角色的用户
            result = await db.execute(
                select(User).where(
                    User.role_codes.op('LIKE')('%agent%') |
                    User.role_codes.op('LIKE')('%customer_service%')
                )
            )
            cs_users = result.scalars().all()

            # 查找所有客服记录
            result = await db.execute(select(CustomerService))
            agents = result.scalars().all()

            # 尝试按名称匹配
            for agent in agents:
                if agent.user_id:
                    continue

                for user in cs_users:
                    if user.nickname == agent.name or user.username == agent.name:
                        agent.user_id = user.id
                        print(f"  ✅ 关联: {agent.name} -> {user.username} (ID: {user.id})")
                        break

            await db.commit()

        print("\n✅ 迁移完成！")

        # 显示结果
        async with async_session_factory() as db:
            result = await db.execute(select(CustomerService))
            agents = result.scalars().all()
            print("\n客服列表：")
            for agent in agents:
                user_info = f" -> {agent.user.username}" if agent.user else " (未关联)"
                print(f"  - {agent.name}{user_info} [{agent.online_status}]")

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(migrate())
