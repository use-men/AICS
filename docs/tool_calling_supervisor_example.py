"""
Tool Calling + SupervisorAgent 使用示例

演示如何使用集成 Tool Calling 的 SupervisorAgent。
"""

import asyncio
import json
from app.ai.schemas import AgentState
from app.ai.agents.supervisor import SupervisorAgent, supervisor_agent
from app.ai.agents.tool_calling import tool_calling_agent
from app.ai.tools import tool_registry


# ============================================================
#  示例 1: 直接使用 ToolCallingAgent
# ============================================================


async def example_tool_calling_agent():
    """直接使用 ToolCallingAgent"""
    print("\n" + "=" * 60)
    print("示例 1: 直接使用 ToolCallingAgent")
    print("=" * 60)

    # 测试用例
    test_cases = [
        "查询工单 TK000001 的状态",
        "订单 ORD20260606001 的支付状态",
        "退款多久到账？",
        "帮我搜索知识库：如何重置密码",
        "今天天气怎么样？",
    ]

    for user_input in test_cases:
        print(f"\n用户问题: {user_input}")

        state = AgentState(
            user_input=user_input,
            user_id=1,
            conversation_id="test_chat_001",
        )

        result = await tool_calling_agent.run(state)

        print(f"工具调用日志:")
        for log in result.tool_logs:
            print(f"  - {log.tool_name}: {log.status} ({log.duration_ms:.2f}ms)")
            print(f"    输入: {log.tool_input}")
            if log.tool_output:
                print(f"    输出: {str(log.tool_output)[:100]}...")

        print(f"metadata: {result.metadata.get('tool_results', {})}")


# ============================================================
#  示例 2: 使用 SupervisorAgent（集成 Tool Calling）
# ============================================================


async def example_supervisor_with_tools():
    """使用集成 Tool Calling 的 SupervisorAgent"""
    print("\n" + "=" * 60)
    print("示例 2: 使用 SupervisorAgent（集成 Tool Calling）")
    print("=" * 60)

    # 测试用例
    test_cases = [
        "查询工单 TK000001 的状态",
        "订单 ORD20260606001 的支付状态",
        "退款多久到账？",
    ]

    for user_input in test_cases:
        print(f"\n用户问题: {user_input}")

        state = AgentState(
            user_input=user_input,
            user_id=1,
            conversation_id="test_chat_002",
        )

        result = await supervisor_agent.run(state)

        print(f"\n执行结果:")
        print(f"  trace_id: {result.trace_id}")
        print(f"  answer: {result.answer[:100]}..." if result.answer else "  answer: None")
        print(f"  need_human: {result.need_human}")
        print(f"  status: {result.status.value}")

        print(f"\n工具调用日志:")
        for log in result.tool_logs:
            print(f"  - {log.tool_name}: {log.status}")

        print(f"\nAgent 执行日志:")
        for log in result.agent_logs:
            print(f"  - {log.agent_name}: {log.status} ({log.duration_ms:.2f}ms)")

        print(f"\n总耗时: {result.get_total_duration_ms():.2f}ms")


# ============================================================
#  示例 3: 查看工具 Schema
# ============================================================


async def example_tool_schemas():
    """查看工具 Schema"""
    print("\n" + "=" * 60)
    print("示例 3: 查看工具 Schema")
    print("=" * 60)

    # 获取所有工具 Schema
    schemas = tool_registry.get_schemas()

    print(f"\n已注册工具数量: {len(schemas)}")

    for schema in schemas:
        print(f"\n工具: {schema['name']}")
        print(f"  描述: {schema['description']}")
        print(f"  参数:")
        for param_name, param_info in schema['parameters']['properties'].items():
            required = param_name in schema['parameters'].get('required', [])
            print(f"    - {param_name}: {param_info.get('type', 'unknown')} {'(必填)' if required else '(可选)'}")
            if 'description' in param_info:
                print(f"      描述: {param_info['description']}")


# ============================================================
#  示例 4: 自定义工具
# ============================================================


from app.ai.tools.base import BaseTool, ToolParameter, ToolResult, ToolStatus


class QueryUserTool(BaseTool):
    """用户查询工具"""

    @property
    def name(self) -> str:
        return "query_user"

    @property
    def description(self) -> str:
        return "查询用户信息，包括用户名、邮箱、手机号等"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="user_id", type="int", description="用户ID", required=True),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        user_id = kwargs.get("user_id")
        if not user_id:
            return ToolResult(status=ToolStatus.ERROR, error="缺少 user_id")

        # 模拟查询
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "user_id": user_id,
                "username": f"user_{user_id}",
                "email": f"user_{user_id}@example.com",
                "phone": "138****1234",
            },
        )


async def example_custom_tool():
    """自定义工具"""
    print("\n" + "=" * 60)
    print("示例 4: 自定义工具")
    print("=" * 60)

    # 注册自定义工具
    tool_registry.register(QueryUserTool())

    # 执行
    result = await tool_registry.execute("query_user", user_id=123)
    print(f"\n查询用户 123:")
    print(f"  状态: {result.status.value}")
    print(f"  数据: {result.data}")

    # 测试 ToolCallingAgent
    state = AgentState(
        user_input="查询用户 123 的信息",
        user_id=1,
        conversation_id="test_chat_003",
    )

    result = await tool_calling_agent.run(state)

    print(f"\nToolCallingAgent 结果:")
    print(f"  工具调用: {len(result.tool_logs)} 次")
    for log in result.tool_logs:
        print(f"    - {log.tool_name}: {log.status}")


# ============================================================
#  主函数
# ============================================================


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("Tool Calling + SupervisorAgent 使用示例")
    print("=" * 60)

    # 运行示例
    await example_tool_calling_agent()
    await example_supervisor_with_tools()
    await example_tool_schemas()
    await example_custom_tool()

    print("\n" + "=" * 60)
    print("所有示例执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())