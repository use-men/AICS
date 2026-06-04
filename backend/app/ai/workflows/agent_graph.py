"""
AgentGraph — 基于 LangGraph 的多 Agent 协作工作流。

节点: Classification → Priority → Knowledge → Dispatch → Response
流程: 用户问题 → 分类 → 优先级 → 知识检索 → 派单 → 生成回答
"""

import json
import logging
from typing import Any, TypedDict, Annotated

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


# ============================================================
#  State 定义
# ============================================================

class AgentState(TypedDict):
    """工作流状态"""
    # ---- 输入 ----
    user_question: str               # 用户原始问题
    conversation_id: str             # 会话ID
    user_id: int | None              # 用户ID
    user_level: str                  # 用户等级
    complaint_count: int             # 历史投诉次数

    # ---- Classification 结果 ----
    ticket_type: str                 # 工单类型
    type_name: str                   # 类型中文名
    classification_confidence: float # 分类置信度

    # ---- Priority 结果 ----
    priority: str                    # 优先级
    priority_reason: str             # 优先级原因

    # ---- Knowledge 结果 ----
    knowledge_answer: str            # 知识库回答
    knowledge_sources: list[dict]    # 引用来源
    need_human: bool                 # 是否需要转人工

    # ---- Dispatch 结果 ----
    service_id: int | None           # 客服ID
    service_name: str                # 客服姓名
    service_load: float              # 客服负载率

    # ---- 最终输出 ----
    final_answer: str                # 最终回答
    ticket_id: int | None            # 工单ID
    steps: list[dict]                # 执行步骤
    error: str | None                # 错误信息


# ============================================================
#  节点函数
# ============================================================

async def classification_node(state: AgentState) -> dict:
    """节点1: 工单分类"""
    logger.info("[Graph] → ClassificationNode")

    try:
        from app.ai.agents.ticket_classifier import TicketClassificationAgent, TICKET_TYPES

        agent = TicketClassificationAgent()
        input_text = json.dumps({
            "title": state["user_question"][:50],
            "content": state["user_question"],
        }, ensure_ascii=False)

        raw = await agent.invoke(input_text)
        result = json.loads(raw)

        ticket_type = result.get("ticket_type", "after_sales")
        type_name = TICKET_TYPES.get(ticket_type, "售后咨询")

        return {
            "ticket_type": ticket_type,
            "type_name": type_name,
            "classification_confidence": result.get("confidence", 0.5),
            "steps": state.get("steps", []) + [{
                "step": "classification",
                "result": f"{type_name} ({result.get('confidence', 0.5)})",
            }],
        }
    except Exception as e:
        logger.error("[Graph] Classification 失败: %s", e)
        return {
            "ticket_type": "after_sales",
            "type_name": "售后咨询",
            "classification_confidence": 0.5,
            "error": f"分类失败: {str(e)}",
            "steps": state.get("steps", []) + [{"step": "classification", "error": str(e)}],
        }


async def priority_node(state: AgentState) -> dict:
    """节点2: 优先级分析"""
    logger.info("[Graph] → PriorityNode")

    try:
        from app.ai.agents.priority_analyzer import PriorityAnalyzerAgent

        agent = PriorityAnalyzerAgent()
        input_text = json.dumps({
            "title": state["user_question"][:50],
            "content": state["user_question"],
            "user_level": state.get("user_level", "normal"),
            "complaint_count": state.get("complaint_count", 0),
        }, ensure_ascii=False)

        raw = await agent.invoke(input_text)
        result = json.loads(raw)

        return {
            "priority": result.get("priority", "medium"),
            "priority_reason": result.get("reason", ""),
            "steps": state.get("steps", []) + [{
                "step": "priority",
                "result": f"{result.get('priority', 'medium')} — {result.get('reason', '')}",
            }],
        }
    except Exception as e:
        logger.error("[Graph] Priority 失败: %s", e)
        return {
            "priority": "medium",
            "priority_reason": "分析失败",
            "steps": state.get("steps", []) + [{"step": "priority", "error": str(e)}],
        }


async def knowledge_node(state: AgentState) -> dict:
    """节点3: 知识库检索"""
    logger.info("[Graph] → KnowledgeNode")

    try:
        from app.ai.agents.customer_service import CustomerServiceAgent

        agent = CustomerServiceAgent()
        raw = await agent.invoke(
            state["user_question"],
            conversation_id=state.get("conversation_id", "default"),
            user_id=state.get("user_id"),
        )
        result = json.loads(raw)

        return {
            "knowledge_answer": result.get("answer", ""),
            "knowledge_sources": result.get("sources", []),
            "need_human": result.get("need_human", False),
            "ticket_id": result.get("ticket_id"),
            "steps": state.get("steps", []) + [{
                "step": "knowledge",
                "result": "转人工" if result.get("need_human") else "已回答",
            }],
        }
    except Exception as e:
        logger.error("[Graph] Knowledge 失败: %s", e)
        return {
            "knowledge_answer": "抱歉，知识库暂时不可用",
            "knowledge_sources": [],
            "need_human": True,
            "steps": state.get("steps", []) + [{"step": "knowledge", "error": str(e)}],
        }


async def dispatch_node(state: AgentState) -> dict:
    """节点4: 智能派单"""
    logger.info("[Graph] → DispatchNode")

    # 如果不需要转人工，跳过派单
    if not state.get("need_human", False):
        return {
            "service_id": None,
            "service_name": "",
            "service_load": 0.0,
            "steps": state.get("steps", []) + [{
                "step": "dispatch",
                "result": "跳过（AI已回答）",
            }],
        }

    try:
        from app.ai.agents.dispatcher import dispatch_agent
        from app.core.database import async_session_factory

        async with async_session_factory() as db:
            agent = await dispatch_agent.dispatch(
                ticket_type=state.get("ticket_type", "after_sales"),
                priority=state.get("priority", "medium"),
                db=db,
            )

        if agent is None:
            return {
                "service_id": None,
                "service_name": "",
                "service_load": 0.0,
                "steps": state.get("steps", []) + [{
                    "step": "dispatch",
                    "result": "无可用客服",
                }],
            }

        return {
            "service_id": agent.id,
            "service_name": agent.name,
            "service_load": agent.load_ratio,
            "steps": state.get("steps", []) + [{
                "step": "dispatch",
                "result": f"{agent.name} (负载: {agent.load_ratio:.0%})",
            }],
        }
    except Exception as e:
        logger.error("[Graph] Dispatch 失败: %s", e)
        return {
            "service_id": None,
            "service_name": "",
            "steps": state.get("steps", []) + [{"step": "dispatch", "error": str(e)}],
        }


async def response_node(state: AgentState) -> dict:
    """节点5: 生成最终回答"""
    logger.info("[Graph] → ResponseNode")

    if state.get("need_human", False):
        # 转人工场景
        service_name = state.get("service_name", "")
        if service_name:
            final_answer = f"正在为您转接人工客服 {service_name}，请稍候..."
        else:
            final_answer = "正在为您转接人工客服，请稍候..."

        # 自动创建工单
        ticket_id = state.get("ticket_id")
        if not ticket_id:
            from app.ai.agents.ticket_creator import TicketCreationAgent
            creator = TicketCreationAgent()
            raw = await creator.invoke(
                state["user_question"],
                conversation_id=state.get("conversation_id", "default"),
                user_id=state.get("user_id"),
            )
            result = json.loads(raw)
            ticket_id = result.get("ticket_id")

        return {
            "final_answer": final_answer,
            "ticket_id": ticket_id,
            "steps": state.get("steps", []) + [{
                "step": "response",
                "result": f"转人工 | 工单: {ticket_id}",
            }],
        }
    else:
        # AI 直接回答
        return {
            "final_answer": state.get("knowledge_answer", "抱歉，暂时无法回答"),
            "ticket_id": None,
            "steps": state.get("steps", []) + [{
                "step": "response",
                "result": "AI直接回答",
            }],
        }


# ============================================================
#  路由函数
# ============================================================

def should_dispatch(state: AgentState) -> str:
    """判断是否需要派单"""
    if state.get("need_human", False):
        return "dispatch"
    return "response"


# ============================================================
#  Graph 定义
# ============================================================

def build_agent_graph() -> StateGraph:
    """
    构建 LangGraph 工作流。

    流程:
        START → Classification → Priority → Knowledge → Dispatch/Response → END
    """
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("classification", classification_node)
    graph.add_node("priority", priority_node)
    graph.add_node("knowledge", knowledge_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("response", response_node)

    # 设置入口
    graph.set_entry_point("classification")

    # 添加边
    graph.add_edge("classification", "priority")
    graph.add_edge("priority", "knowledge")

    # 条件路由: Knowledge → Dispatch 或 Response
    graph.add_conditional_edges(
        "knowledge",
        should_dispatch,
        {
            "dispatch": "dispatch",
            "response": "response",
        },
    )

    graph.add_edge("dispatch", "response")
    graph.add_edge("response", END)

    return graph


# ============================================================
#  工作流执行
# ============================================================

class AgentGraphWorkflow:
    """
    LangGraph 多 Agent 协作工作流。

    使用方式:
        workflow = AgentGraphWorkflow()
        result = await workflow.run("我的产品无法登录")
    """

    def __init__(self):
        self._graph = build_agent_graph()
        self._app = self._graph.compile()

    async def run(
        self,
        user_question: str,
        conversation_id: str = "default",
        user_id: int | None = None,
        user_level: str = "normal",
        complaint_count: int = 0,
    ) -> dict[str, Any]:
        """
        执行工作流。

        Args:
            user_question: 用户问题
            conversation_id: 会话ID
            user_id: 用户ID
            user_level: 用户等级
            complaint_count: 历史投诉次数

        Returns:
            工作流执行结果
        """
        initial_state: AgentState = {
            "user_question": user_question,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "user_level": user_level,
            "complaint_count": complaint_count,
            "ticket_type": "",
            "type_name": "",
            "classification_confidence": 0.0,
            "priority": "",
            "priority_reason": "",
            "knowledge_answer": "",
            "knowledge_sources": [],
            "need_human": False,
            "service_id": None,
            "service_name": "",
            "service_load": 0.0,
            "final_answer": "",
            "ticket_id": None,
            "steps": [],
            "error": None,
        }

        result = await self._app.ainvoke(initial_state)
        return result

    def get_mermaid(self) -> str:
        """生成 Mermaid 流程图"""
        return GRAPH_MERMAID


# ============================================================
#  Mermaid 流程图
# ============================================================

GRAPH_MERMAID = """
graph TD
    A([开始]) --> B[ClassificationAgent<br/>工单分类]
    B --> C[PriorityAgent<br/>优先级分析]
    C --> D{KnowledgeAgent<br/>知识库检索}
    D -->|需要转人工| E[DispatchAgent<br/>智能派单]
    D -->|AI可回答| F[ResponseAgent<br/>生成回答]
    E --> F
    F --> G([结束])

    style A fill:#4CAF50,color:#fff
    style B fill:#2196F3,color:#fff
    style C fill:#FF9800,color:#fff
    style D fill:#9C27B0,color:#fff
    style E fill:#F44336,color:#fff
    style F fill:#00BCD4,color:#fff
    style G fill:#4CAF50,color:#fff
"""


# ---- 全局单例 ----

agent_graph_workflow = AgentGraphWorkflow()
