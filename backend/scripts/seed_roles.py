"""
角色种子数据 — 初始化内置角色。

使用方式:
    python scripts/seed_roles.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_factory, engine, Base
from app.models.user import Role
from sqlalchemy import select


# 内置角色定义
BUILTIN_ROLES = [
    {"name": "管理员", "code": "admin", "description": "系统管理员，拥有所有权限"},
    {"name": "客服", "code": "agent", "description": "客服人员，处理用户工单和咨询"},
    {"name": "普通用户", "code": "user", "description": "普通用户，可以提交工单和咨询"},
]


async def seed_roles():
    """初始化角色数据"""
    print("正在初始化角色数据...")

    try:
        # 确保表存在
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session_factory() as db:
            for role_data in BUILTIN_ROLES:
                # 检查是否已存在
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

        print("\n✅ 角色数据初始化完成！")

        # 显示所有角色
        async with async_session_factory() as db:
            result = await db.execute(select(Role).order_by(Role.id))
            roles = result.scalars().all()
            print("\n当前角色列表：")
            for role in roles:
                print(f"  - {role.name} ({role.code}): {role.description or '-'}")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(seed_roles())
