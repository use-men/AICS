"""
Tool Calling 使用示例

演示如何使用工具注册中心和各个工具。
"""

import asyncio
import json
from app.ai.tools import (
    tool_registry,
    query_ticket_tool,
    query_order_tool,
    query_refund_tool,
    search_knowledge_tool,
    search_web_tool,
)


# ============================================================
#  示例 1: 使用 ToolRegistry
# ============================================================


async def example_tool_registry():
    """使用 ToolRegistry 执行工具"""
    print("\n" + "=" * 60)
    print("示例 1: 使用 ToolRegistry")
    print("=" * 60)

    # 列出所有工具
    print("\n已注册的工具:")
    for tool_info in tool_registry.list_tools():
        print(f"  - {tool_info['name']}: {tool_info['description']}")

    # 获取工具 Schema
    print("\n工具 Schema:")
    schemas = tool_registry.get_schemas()
    for schema in schemas[:2]:  # 只显示前2个
        print(f"\n  {schema['name']}:")
        print(f"    描述: {schema['description']}")
        print(f"    参数: {json.dumps(schema['parameters']['properties'], indent=6, ensure_ascii=False)}")

    # 执行工具
    print("\n执行工单查询工具:")
    result = await tool_registry.execute("query_ticket", ticket_id=1)
    print(f"  状态: {result.status.value}")
    print(f"  数据: {result.data}")
    print(f"  耗时: {result.execution_time_ms:.2f}ms")


# ============================================================
#  示例 2: 直接使用工具
# ============================================================


async def example_direct_tool():
    """直接使用工具实例"""
    print("\n" + "=" * 60)
    print("示例 2: 直接使用工具")
    print("=" * 60)

    # 工单查询
    print("\n1. 工单查询:")
    result = await query_ticket_tool.execute(ticket_id=1)
    print(f"   状态: {result.status.value}")
    if result.is_success():
        print(f"   工单号: {result.data.get('ticket_no')}")
        print(f"   状态: {result.data.get('status_label')}")
        print(f"   优先级: {result.data.get('priority_label')}")

    # 订单查询
    print("\n2. 订单查询:")
    result = await query_order_tool.execute(order_no="ORD20260606001")
    print(f"   状态: {result.status.value}")
    if result.is_success():
        print(f"   订单号: {result.data.get('order_no')}")
        print(f"   支付状态: {result.data.get('payment_status_label')}")
        print(f"   金额: {result.data.get('total_amount')} 元")

    # 退款查询
    print("\n3. 退款查询:")
    result = await query_refund_tool.execute(order_no="ORD20260606001")
    print(f"   状态: {result.status.value}")
    if result.is_success():
        print(f"   退款状态: {result.data.get('refund_status_label')}")
        print(f"   退款金额: {result.data.get('refund_amount')} 元")
        print(f"   预计到账: {result.data.get('estimated_arrival')}")


# ============================================================
#  示例 3: 知识库搜索
# ============================================================


async def example_knowledge_search():
    """知识库搜索"""
    print("\n" + "=" * 60)
    print("示例 3: 知识库搜索")
    print("=" * 60)

    print("\n搜索: 退款到账时间")
    result = await search_knowledge_tool.execute(query="退款到账时间", top_k=3)

    print(f"状态: {result.status.value}")
    if result.is_success():
        print(f"找到 {result.data.get('total')} 条结果:")
        for item in result.data.get("results", []):
            print(f"\n  [{item['index']}] 相关度: {item['score']}")
            print(f"      问题: {item['question']}")
            print(f"      回答: {item['answer'][:100]}...")


# ============================================================
#  示例 4: 联网搜索
# ============================================================


async def example_web_search():
    """联网搜索"""
    print("\n" + "=" * 60)
    print("示例 4: 联网搜索")
    print("=" * 60)

    print("\n搜索: 今天天气")
    result = await search_web_tool.execute(query="今天天气", max_results=3)

    print(f"状态: {result.status.value}")
    if result.is_success():
        print(f"找到 {result.data.get('total')} 条结果:")
        for item in result.data.get("results", []):
            print(f"\n  - {item['title']}")
            print(f"    链接: {item['url']}")
            print(f"    摘要: {item['content'][:100]}...")
    else:
        print(f"错误: {result.error}")


# ============================================================
#  示例 5: 自定义工具
# ============================================================


from app.ai.tools.base import BaseTool, ToolParameter, ToolResult, ToolStatus


class MyCustomTool(BaseTool):
    """自定义工具示例"""

    @property
    def name(self) -> str:
        return "my_custom_tool"

    @property
    def description(self) -> str:
        return "我的自定义工具"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="input", type="str", description="输入内容", required=True),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        input_text = kwargs.get("input", "")
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"message": f"处理完成: {input_text}"},
        )


async def example_custom_tool():
    """自定义工具"""
    print("\n" + "=" * 60)
    print("示例 5: 自定义工具")
    print("=" * 60)

    # 注册自定义工具
    tool_registry.register(MyCustomTool())

    # 执行
    result = await tool_registry.execute("my_custom_tool", input="测试输入")
    print(f"\n状态: {result.status.value}")
    print(f"数据: {result.data}")


# ============================================================
#  主函数
# ============================================================


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("Tool Calling 使用示例")
    print("=" * 60)

    # 运行示例
    await example_tool_registry()
    await example_direct_tool()
    await example_knowledge_search()
    await example_web_search()
    await example_custom_tool()

    print("\n" + "=" * 60)
    print("所有示例执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())