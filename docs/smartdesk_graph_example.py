"""
SmartDeskGraph 使用示例

演示如何使用 LangGraph 工作流进行智能客服调度。
"""

import asyncio
import json
from app.ai.schemas import AgentState
from app.ai.workflows.smartdesk_graph import SmartDeskGraph, smartdesk_graph
from app.ai.agents.supervisor import SupervisorAgent, supervisor_agent


# ============================================================
#  示例 1: 直接使用 SmartDeskGraph
# ============================================================


async def example_direct_graph():
    """直接使用 SmartDeskGraph"""
    print("\n" + "=" * 60)
    print("示例 1: 直接使用 SmartDeskGraph")
    print("=" * 60)

    # 创建初始状态
    state = AgentState(
        user_input="退款多久到账？",
        user_id=1,
        conversation_id="chat_001",
    )

    print(f"\n初始状态:")
    print(f"  trace_id: {state.trace_id}")
    print(f"  user_input: {state.user_input}")
    print(f"  status: {state.status}")

    # 执行工作流
    result = await smartdesk_graph.invoke(state)

    # 输出结果
    print(f"\n执行结果:")
    print(f"  trace_id: {result.trace_id}")
    print(f"  answer: {result.answer[:100]}...")
    print(f"  need_human: {result.need_human}")
    print(f"  status: {result.status.value}")
    print(f"  total_duration: {result.get_total_duration_ms():.2f}ms")

    # 输出 Agent 日志
    print(f"\nAgent 执行日志:")
    for log in result.agent_logs:
        print(f"  - {log.agent_name}: {log.status} ({log.duration_ms:.2f}ms)")

    return result


# ============================================================
#  示例 2: 使用 SupervisorAgent（兼容接口）
# ============================================================


async def example_supervisor_agent():
    """使用 SupervisorAgent 兼容接口"""
    print("\n" + "=" * 60)
    print("示例 2: 使用 SupervisorAgent")
    print("=" * 60)

    # 方式 1: 使用 run 方法（新接口）
    state = AgentState(
        user_input="支付成功但订单没生成",
        user_id=2,
        conversation_id="chat_002",
    )

    print(f"\n初始状态:")
    print(f"  trace_id: {state.trace_id}")
    print(f"  user_input: {state.user_input}")

    result = await supervisor_agent.run(state)

    print(f"\n执行结果:")
    print(f"  trace_id: {result.trace_id}")
    print(f"  need_human: {result.need_human}")
    print(f"  ticket_type: {result.ticket_type}")
    print(f"  ticket_priority: {result.ticket_priority}")
    print(f"  ticket_id: {result.ticket_id}")
    print(f"  assignee_id: {result.assignee_id}")

    # 方式 2: 使用 invoke 方法（兼容旧接口）
    print("\n--- 使用 invoke 方法 ---")
    json_result = await supervisor_agent.invoke(
        "如何重置密码？",
        user_id=3,
        conversation_id="chat_003",
    )

    data = json.loads(json_result)
    print(f"\nJSON 结果:")
    print(f"  trace_id: {data['trace_id']}")
    print(f"  answer: {data['answer'][:100]}...")
    print(f"  need_human: {data['need_human']}")
    print(f"  agent_logs: {len(data['agent_logs'])} 个 Agent 执行")

    return result


# ============================================================
#  示例 3: 查看工作流图
# ============================================================


async def example_visualize_graph():
    """可视化工作流图"""
    print("\n" + "=" * 60)
    print("示例 3: 工作流可视化")
    print("=" * 60)

    # 获取图对象
    graph = smartdesk_graph.get_graph()

    # 打印图结构
    print("\n工作流节点:")
    for node in graph.nodes:
        print(f"  - {node}")

    print("\n工作流边:")
    for edge in graph.edges:
        print(f"  - {edge}")

    # 生成 Mermaid 图（可选）
    print("\nMermaid 流程图:")
    print("""
```mermaid
graph TD
    START([START]) --> knowledge_node[knowledge_node]
    knowledge_node --> decision{need_human?}
    decision -->|False| END([END])
    decision -->|True| classification_node[classification_node]
    classification_node --> priority_node[priority_node]
    priority_node --> ticket_creation_node[ticket_creation_node]
    ticket_creation_node --> dispatch_node[dispatch_node]
    dispatch_node --> END
```
    """)


# ============================================================
#  示例 4: 错误处理
# ============================================================


async def example_error_handling():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("示例 4: 错误处理")
    print("=" * 60)

    # 创建初始状态
    state = AgentState(
        user_input="测试错误处理",
        user_id=4,
        conversation_id="chat_004",
    )

    # 正常执行
    result = await supervisor_agent.run(state)

    print(f"\n执行结果:")
    print(f"  trace_id: {result.trace_id}")
    print(f"  status: {result.status.value}")
    print(f"  error: {result.error}")

    # 检查 Agent 日志
    print(f"\nAgent 日志:")
    for log in result.agent_logs:
        status_icon = "✓" if log.status == "completed" else "✗"
        print(f"  {status_icon} {log.agent_name}: {log.status}")
        if log.error:
            print(f"    错误: {log.error}")


# ============================================================
#  主函数
# ============================================================


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("SmartDeskGraph 使用示例")
    print("=" * 60)

    # 运行示例
    await example_direct_graph()
    await example_supervisor_agent()
    await example_visualize_graph()
    await example_error_handling()

    print("\n" + "=" * 60)
    print("所有示例执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())