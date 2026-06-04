"""
种子数据：创建三端测试用户 + 角色 + 权限。

运行方式：
    cd SmartDesk/backend
    python -m scripts.seed
"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import asyncio
import sys
from pathlib import Path

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, Base, engine
from app.core.security import hash_password
from app.models.user import User, Role, Permission, user_roles, role_permissions


# ============================================================
#  权限定义
# ============================================================

PERMISSIONS = [
    # 用户端
    ("ticket:view", "查看工单"),
    ("ticket:create", "创建工单"),
    ("ticket:reply", "回复工单"),
    # 客服端
    ("ticket:assign", "分配工单"),
    ("ticket:transfer", "转派工单"),
    ("ticket:close", "关闭工单"),
    # 管理端
    ("user:view", "查看用户"),
    ("user:create", "创建用户"),
    ("user:edit", "编辑用户"),
    ("user:delete", "删除用户"),
    ("role:view", "查看角色"),
    ("role:manage", "管理角色"),
    ("system:config", "系统配置"),
    ("system:log", "查看日志"),
    ("knowledge:manage", "知识库管理"),
    ("payment:view", "查看支付"),
    ("payment:refund", "退款审核"),
]


# ============================================================
#  角色定义
# ============================================================

ROLES = {
    "user": {
        "name": "普通用户",
        "code": "user",
        "permissions": ["ticket:view", "ticket:create", "ticket:reply"],
    },
    "agent": {
        "name": "客服人员",
        "code": "customer_service",
        "permissions": [
            "ticket:view", "ticket:create", "ticket:reply",
            "ticket:assign", "ticket:transfer", "ticket:close",
            "knowledge:manage",
        ],
    },
    "supervisor": {
        "name": "客服主管",
        "code": "supervisor",
        "permissions": [
            "ticket:view", "ticket:create", "ticket:reply",
            "ticket:assign", "ticket:transfer", "ticket:close",
            "knowledge:manage", "payment:view",
        ],
    },
    "admin": {
        "name": "超级管理员",
        "code": "admin",
        "permissions": [
            "ticket:view", "ticket:create", "ticket:reply",
            "ticket:assign", "ticket:transfer", "ticket:close",
            "user:view", "user:create", "user:edit", "user:delete",
            "role:view", "role:manage",
            "system:config", "system:log",
            "knowledge:manage",
            "payment:view", "payment:refund",
        ],
    },
}


# ============================================================
#  测试用户
# ============================================================

USERS = [
    # ---- 用户端 ----
    {
        "username": "zhangsan",
        "email": "zhangsan@test.com",
        "phone": "13800000001",
        "password": "123456",
        "nickname": "张三",
        "role": "user",
    },
    {
        "username": "lisi",
        "email": "lisi@test.com",
        "phone": "13800000002",
        "password": "123456",
        "nickname": "李四",
        "role": "user",
    },
    # ---- 客服端 ----
    {
        "username": "cs_1001",
        "email": "cs1001@smartdesk.com",
        "phone": "13800000011",
        "password": "123456",
        "nickname": "客服-王芳",
        "employee_id": "cs_1001",
        "role": "agent",
    },
    {
        "username": "cs_1002",
        "email": "cs1002@smartdesk.com",
        "phone": "13800000012",
        "password": "123456",
        "nickname": "客服-李明",
        "employee_id": "cs_1002",
        "role": "agent",
    },
    {
        "username": "cs_1003",
        "email": "cs1003@smartdesk.com",
        "phone": "13800000013",
        "password": "123456",
        "nickname": "主管-赵强",
        "employee_id": "cs_1003",
        "role": "supervisor",
    },
    # ---- 管理端 ----
    {
        "username": "admin",
        "email": "admin@smartdesk.com",
        "phone": "13800000100",
        "password": "admin123",
        "nickname": "超级管理员",
        "role": "admin",
    },
]


# ============================================================
#  主函数
# ============================================================

async def seed():
    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据表已创建")

    async with async_session_factory() as db:
        # ---- 1. 创建权限 ----
        perm_map: dict[str, Permission] = {}
        for code, name in PERMISSIONS:
            result = await db.execute(select(Permission).where(Permission.code == code))
            perm = result.scalar_one_or_none()
            if not perm:
                perm = Permission(code=code, name=name)
                db.add(perm)
                await db.flush()
            perm_map[code] = perm
        print(f"✅ 权限已就绪 ({len(perm_map)} 个)")

        # ---- 2. 创建角色 ----
        role_map: dict[str, Role] = {}
        for key, role_def in ROLES.items():
            result = await db.execute(select(Role).where(Role.code == role_def["code"]))
            role = result.scalar_one_or_none()
            if not role:
                role = Role(name=role_def["name"], code=role_def["code"])
                db.add(role)
                await db.flush()
            # 绑定权限
            role.permissions = [perm_map[p] for p in role_def["permissions"] if p in perm_map]
            role_map[key] = role
        print(f"✅ 角色已就绪 ({len(role_map)} 个)")

        # ---- 3. 创建用户 ----
        for u in USERS:
            result = await db.execute(select(User).where(User.username == u["username"]))
            existing = result.scalar_one_or_none()
            if existing:
                print(f"   ⏭  用户 {u['username']} 已存在，跳过")
                continue

            user = User(
                username=u["username"],
                email=u["email"],
                phone=u.get("phone"),
                hashed_password=hash_password(u["password"]),
                nickname=u.get("nickname"),
                employee_id=u.get("employee_id"),
            )
            user.roles = [role_map[u["role"]]]
            db.add(user)
            await db.flush()
            print(f"   ✅ 创建用户: {u['username']} ({u['nickname']})")

        await db.commit()

    print("\n" + "=" * 50)
    print("🎉 种子数据初始化完成！")
    print("=" * 50)
    print_login_table()


def print_login_table():
    """打印登录信息表格"""
    print("\n📋 三端登录账号：\n")
    print("┌──────────┬─────────────────┬──────────┬──────────────────────────┐")
    print("│ 端       │ 账号            │ 密码     │ 登录页                   │")
    print("├──────────┼─────────────────┼──────────┼──────────────────────────┤")
    print("│ 用户端   │ zhangsan        │ 123456   │ /login (手机或邮箱登录)  │")
    print("│ 用户端   │ 13800000001     │ 验证码   │ /login (手机验证码登录)  │")
    print("├──────────┼─────────────────┼──────────┼──────────────────────────┤")
    print("│ 客服端   │ cs_1001         │ 123456   │ /cs/login                │")
    print("│ 客服端   │ cs_1002         │ 123456   │ /cs/login                │")
    print("│ 客服端   │ cs_1003 (主管)  │ 123456   │ /cs/login                │")
    print("├──────────┼─────────────────┼──────────┼──────────────────────────┤")
    print("│ 管理端   │ admin           │ admin123 │ /admin/login (两步验证)  │")
    print("└──────────┴─────────────────┴──────────┴──────────────────────────┘")


if __name__ == "__main__":
    asyncio.run(seed())
