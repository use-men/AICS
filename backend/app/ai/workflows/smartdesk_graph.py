"""
SmartDeskGraph — 基于 LangGraph 的智能客服工作流。

流程:
    START → tool_calling_node → knowledge_node → 判断 need_human
        ├─ False → END
        └─ True → classification_node → priority_node → ticket_creation_node → dispatch_node → END

使用 LangGraph StateGraph 实现状态管理和条件路由。
"""

import json
import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from app.ai.schemas import AgentState, AgentType, TaskStatus

logger = logging.getLogger(__name__)


# ============================================================
#  节点函数
# ============================================================


async def tool_calling_node(state: AgentState) -> dict:
    """
    Tool Calling 节点。

    分析用户问题，判断是否需要调用工具。
    """
    logger.info("[Graph] tool_calling_node 开始 | trace_id: %s", state.trace_id)

    state.start_agent(
        agent_name="tool_calling",
        agent_type=AgentType.TOOL_CALLING,
        input_summary=state.user_input[:200],
    )

    try:
        from app.ai.agents.tool_calling import ToolCallingAgent

        agent = ToolCallingAgent()
        state = await agent.run(state)

        state.complete_agent(output_summary=f"tool_logs: {len(state.tool_logs)}")

        logger.info("[Graph] tool_calling_node 完成 | tool_logs: %d | trace_id: %s",
                    len(state.tool_logs), state.trace_id)

        # 不返回 agent_logs 和 tool_logs，让 LangGraph 使用原始状态
        return {
            "metadata": state.metadata,
            "current_agent": state.current_agent,
        }

    except Exception as e:
        state.fail_agent(str(e))
        logger.error("[Graph] tool_calling_node 失败: %s", e)
        raise


async def knowledge_node(state: AgentState) -> dict:
    """
    知识库检索节点。

    调用 KnowledgeAgent 进行知识库检索，判断是否需要转人工。
    如果有工具调用结果，将其加入到用户输入中。
    """
    logger.info("[Graph] knowledge_node 开始 | trace_id: %s", state.trace_id)

    # 检查是否有工具调用结果
    tool_results = state.metadata.get("tool_results", {})
    if tool_results:
        logger.info("[Graph] 包含工具结果: %s", list(tool_results.keys()))
        # 将工具结果加入到用户输入中
        tool_context = "\n".join([
            f"【{tool_name}查询结果】{json.dumps(result, ensure_ascii=False, default=str)[:500]}"
            for tool_name, result in tool_results.items()
        ])
        state.user_input = f"{state.user_input}\n\n{tool_context}"

    # 开始记录日志
    state.start_agent(
        agent_name="knowledge_agent",
        agent_type=AgentType.KNOWLEDGE,
        input_summary=state.user_input[:200],
    )

    try:
        from app.ai.agents.knowledge_agent import KnowledgeAgent

        agent = KnowledgeAgent()
        state = await agent.run(state)

        # 完成日志
        state.complete_agent(output_summary=state.answer[:200])

        logger.info("[Graph] knowledge_node 完成 | need_human: %s | trace_id: %s",
                    state.need_human, state.trace_id)

        return {
            "answer": state.answer,
            "need_human": state.need_human,
            "transfer_reason": state.transfer_reason,
            "knowledge_results": state.knowledge_results,
            "knowledge_context": state.knowledge_context,
            "confidence_score": state.confidence_score,
            "low_confidence": state.low_confidence,
            "current_agent": state.current_agent,
        }

    except Exception as e:
        state.fail_agent(str(e))
        logger.error("[Graph] knowledge_node 失败: %s", e)
        raise


async def classification_node(state: AgentState) -> dict:
    """
    工单分类节点。

    调用 TicketClassificationAgent 对工单进行分类。
    """
    logger.info("[Graph] classification_node 开始 | trace_id: %s", state.trace_id)

    state.start_agent(
        agent_name="ticket_classifier",
        agent_type=AgentType.TICKET_CLASSIFIER,
        input_summary=state.user_input[:200],
    )

    try:
        from app.ai.agents.ticket_classifier import TicketClassificationAgent
        import json

        agent = TicketClassificationAgent()

        # 构建输入
        input_data = json.dumps({
            "title": state.user_input[:50],
            "content": state.user_input,
        }, ensure_ascii=False)
        state.user_input = input_data

        state = await agent.run(state)

        state.complete_agent(output_summary=f"ticket_type: {state.ticket_type}")

        logger.info("[Graph] classification_node 完成 | type: %s | trace_id: %s",
                    state.ticket_type, state.trace_id)

        return {
            "ticket_type": state.ticket_type,
            "current_agent": state.current_agent,
        }

    except Exception as e:
        state.fail_agent(str(e))
        logger.error("[Graph] classification_node 失败: %s", e)
        raise


async def priority_node(state: AgentState) -> dict:
    """
    优先级分析节点。

    调用 PriorityAnalyzerAgent 分析工单优先级。
    """
    logger.info("[Graph] priority_node 开始 | trace_id: %s", state.trace_id)

    state.start_agent(
        agent_name="priority_analyzer",
        agent_type=AgentType.PRIORITY_ANALYZER,
        input_summary=f"type={state.ticket_type}",
    )

    try:
        from app.ai.agents.priority_analyzer import PriorityAnalyzerAgent
        import json

        agent = PriorityAnalyzerAgent()

        # 构建输入
        input_data = json.dumps({
            "title": state.user_input[:50] if state.user_input else "",
            "content": state.user_input,
            "ticket_type": state.ticket_type,
        }, ensure_ascii=False)
        state.user_input = input_data

        state = await agent.run(state)

        state.complete_agent(output_summary=f"priority: {state.ticket_priority}")

        logger.info("[Graph] priority_node 完成 | priority: %s | trace_id: %s",
                    state.ticket_priority, state.trace_id)

        return {
            "ticket_priority": state.ticket_priority,
            "current_agent": state.current_agent,
        }

    except Exception as e:
        state.fail_agent(str(e))
        logger.error("[Graph] priority_node 失败: %s", e)
        raise


async def ticket_creation_node(state: AgentState) -> dict:
    """
    工单创建节点。

    调用 TicketCreationAgent 创建工单。
    """
    logger.info("[Graph] ticket_creation_node 开始 | trace_id: %s", state.trace_id)

    state.start_agent(
        agent_name="ticket_creator",
        agent_type=AgentType.TICKET_CREATOR,
        input_summary=f"type={state.ticket_type}, priority={state.ticket_priority}",
    )

    try:
        from app.ai.agents.ticket_creator import TicketCreationAgent

        agent = TicketCreationAgent()
        state = await agent.run(state)

        if state.ticket_info:
            state.complete_agent(output_summary=f"ticket_no: {state.ticket_info.ticket_no}")
        else:
            state.complete_agent(output_summary="ticket created")

        logger.info("[Graph] ticket_creation_node 完成 | ticket_id: %s | trace_id: %s",
                    state.ticket_id, state.trace_id)

        return {
            "ticket_id": state.ticket_id,
            "ticket_info": state.ticket_info,
            "current_agent": state.current_agent,
        }

    except Exception as e:
        state.fail_agent(str(e))
        logger.error("[Graph] ticket_creation_node 失败: %s", e)
        raise


async def dispatch_node(state: AgentState) -> dict:
    """
    智能派单节点。

    调用 DispatchAgent 分配客服。
    """
    logger.info("[Graph] dispatch_node 开始 | trace_id: %s", state.trace_id)

    state.start_agent(
        agent_name="dispatcher",
        agent_type=AgentType.DISPATCHER,
        input_summary=f"type={state.ticket_type}, priority={state.ticket_priority}",
    )

    try:
        from app.ai.agents.dispatcher import DispatchAgent

        agent = DispatchAgent()
        state = await agent.run(state)

        if state.assignee_id:
            state.complete_agent(output_summary=f"assignee_id: {state.assignee_id}")
        else:
            state.complete_agent(output_summary="no assignee")

        logger.info("[Graph] dispatch_node 完成 | assignee_id: %s | trace_id: %s",
                    state.assignee_id, state.trace_id)

        return {
            "assignee_id": state.assignee_id,
            "current_agent": state.current_agent,
        }

    except Exception as e:
        state.fail_agent(str(e))
        logger.error("[Graph] dispatch_node 失败: %s", e)
        raise


# ============================================================
#  条件路由函数
# ============================================================


def should_transfer(state: AgentState) -> Literal["classification_node", "__end__"]:
    """
    条件路由：判断是否需要转人工。

    Returns:
        如果 need_human=True，返回 "classification_node"
        如果 need_human=False，返回 "__end__"
    """
    if state.need_human:
        logger.info("[Graph] 路由: 需要转人工 → classification_node | trace_id: %s", state.trace_id)
        return "classification_node"
    else:
        logger.info("[Graph] 路由: 问题已解决 → END | trace_id: %s", state.trace_id)
        return "__end__"


# ============================================================
#  构建 StateGraph
# ============================================================


def build_smartdesk_graph():
    """
    构建 SmartDesk 工作流图。

    流程:
        START → tool_calling_node → knowledge_node → should_transfer
            ├─ False → END
            └─ True → classification_node → priority_node → ticket_creation_node → dispatch_node → END

    Returns:
        编译后的 StateGraph
    """
    # 创建图
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("tool_calling_node", tool_calling_node)
    graph.add_node("knowledge_node", knowledge_node)
    graph.add_node("classification_node", classification_node)
    graph.add_node("priority_node", priority_node)
    graph.add_node("ticket_creation_node", ticket_creation_node)
    graph.add_node("dispatch_node", dispatch_node)

    # 设置入口
    graph.set_entry_point("tool_calling_node")

    # 添加边
    graph.add_edge("tool_calling_node", "knowledge_node")

    # 添加条件路由
    graph.add_conditional_edges(
        "knowledge_node",
        should_transfer,
        {
            "classification_node": "classification_node",
            "__end__": END,
        },
    )

    # 添加线性边
    graph.add_edge("classification_node", "priority_node")
    graph.add_edge("priority_node", "ticket_creation_node")
    graph.add_edge("ticket_creation_node", "dispatch_node")
    graph.add_edge("dispatch_node", END)

    # 编译图
    return graph.compile()


# ============================================================
#  工作流封装类
# ============================================================


class SmartDeskGraph:
    """
    SmartDesk 工作流封装类。

    使用方式:
        graph = SmartDeskGraph()
        result = await graph.invoke(state)
    """

    def __init__(self):
        self._graph = build_smartdesk_graph()
        logger.info("[SmartDeskGraph] 工作流初始化完成")

    async def invoke(self, state: AgentState) -> AgentState:
        """
        执行工作流。

        Args:
            state: 初始 AgentState

        Returns:
            更新后的 AgentState
        """
        logger.info("[SmartDeskGraph] 开始执行 | trace_id: %s | user_input: %s",
                    state.trace_id, state.user_input[:100])

        try:
            # 执行图
            result = await self._graph.ainvoke(state)

            # result 是字典，需要合并回 AgentState
            if isinstance(result, dict):
                for key, value in result.items():
                    if hasattr(state, key):
                        setattr(state, key, value)

            state.status = TaskStatus.COMPLETED

            logger.info("[SmartDeskGraph] 执行完成 | trace_id: %s | status: %s | duration: %.2fms",
                        state.trace_id, state.status.value, state.get_total_duration_ms())

            return state

        except Exception as e:
            state.status = TaskStatus.FAILED
            state.error = str(e)
            logger.error("[SmartDeskGraph] 执行失败 | trace_id: %s | error: %s", state.trace_id, e)
            return state

    def get_graph(self):
        """获取原始图对象（用于可视化）"""
        return self._graph


# ============================================================
#  全局单例
# ============================================================


smartdesk_graph = SmartDeskGraph()