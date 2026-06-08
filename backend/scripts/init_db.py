"""
数据库初始化脚本 — 创建所有表 + 初始化角色数据。

使用方式:
    python scripts/init_db.py
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base, async_session_factory
from app.models.agent_log import AgentExecutionLog, AgentStatistics, ToolExecutionLog
from app.models.user import Role
from sqlalchemy import select


# 内置角色定义
BUILTIN_ROLES = [
    {"name": "管理员", "code": "admin", "description": "系统管理员，拥有所有权限"},
    {"name": "客服", "code": "agent", "description": "客服人员，处理用户工单和咨询"},
    {"name": "普通用户", "code": "user", "description": "普通用户，可以提交工单和咨询"},
]


async def init_database():
    """初始化数据库，创建所有表 + 初始化角色"""
    print("正在初始化数据库...")

    try:
        # 导入所有模型（确保所有表都被注册）
        from app.models import user, ticket, knowledge, customer_service, ticket_message, conversation  # noqa: F401
        from app.models.agent_log import AgentExecutionLog, AgentStatistics

        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ 数据库表创建成功！")
        print("\n已创建的表：")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")

        # 初始化角色数据
        print("\n正在初始化角色数据...")
        async with async_session_factory() as db:
            for role_data in BUILTIN_ROLES:
                result = await db.execute(
                    select(Role).where(Role.code == role_data["code"])
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"  ⏭️  角色已存在: {role_data['name']} ({role_data['code']})")
                else:
                    role = Role(**role_data)
                    db.add(role)
                    print(f"  ✅ 创建角色: {role_data['name']} ({role_data['code']})")

            await db.commit()

        print("\n✅ 数据库初始化完成！")

    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_database())