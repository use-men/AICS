# SmartDeskGraph 工作流文档

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     SmartDeskGraph 工作流                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                                                │
│  │    START    │                                                │
│  └──────┬──────┘                                                │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────┐                                            │
│  │ knowledge_node  │ ← KnowledgeAgent                           │
│  └────────┬────────┘                                            │
│           │                                                     │
│           ▼                                                     │
│    ┌─────────────┐                                              │
│    │ need_human? │                                              │
│    └──────┬──────┘                                              │
│           │                                                     │
│     ┌─────┴─────┐                                               │
│     │           │                                               │
│     ▼           ▼                                               │
│  ┌──────┐  ┌────────────────┐                                   │
│  │ END  │  │ classification │ ← TicketClassificationAgent       │
│  └──────┘  └───────┬────────┘                                   │
│                    │                                            │
│                    ▼                                            │
│             ┌────────────┐                                      │
│             │  priority  │ ← PriorityAnalyzerAgent              │
│             └─────┬──────┘                                      │
│                   │                                             │
│                   ▼                                             │
│          ┌───────────────┐                                      │
│          │ ticket_creation│ ← TicketCreationAgent               │
│          └───────┬───────┘                                      │
│                  │                                              │
│                  ▼                                              │
│            ┌──────────┐                                         │
│            │ dispatch │ ← DispatchAgent                         │
│            └────┬─────┘                                         │
│                 │                                               │
│                 ▼                                               │
│               ┌──────┐                                          │
│               │ END  │                                          │
│               └──────┘                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 节点说明

| 节点 | Agent | 职责 | 输入 | 输出 |
|------|-------|------|------|------|
| knowledge_node | KnowledgeAgent | 知识库检索 | user_input | answer, need_human |
| classification_node | TicketClassificationAgent | 工单分类 | user_input | ticket_type |
| priority_node | PriorityAnalyzerAgent | 优先级分析 | ticket_type | ticket_priority |
| ticket_creation_node | TicketCreationAgent | 创建工单 | user_input, ticket_type | ticket_id, ticket_info |
| dispatch_node | DispatchAgent | 智能派单 | ticket_type, ticket_priority | assignee_id |

---

## 3. 条件路由

```python
def should_transfer(state: AgentState) -> Literal["classification_node", "__end__"]:
    """
    条件路由：判断是否需要转人工。

    Returns:
        如果 need_human=True，返回 "classification_node"
        如果 need_human=False，返回 "__end__"
    """
    if state.need_human:
        return "classification_node"
    else:
        return "__end__"
```

---

## 4. 完整流程

### 场景 1: 问题已解决（不需要转人工）

```
用户: 退款多久到账？
    ↓
KnowledgeAgent: 根据平台规则，退款将在1-3个工作日到账。
    ↓
need_human = False
    ↓
END
```

**执行日志：**

```json
{
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "answer": "根据平台规则，退款将在1-3个工作日到账。",
  "need_human": false,
  "status": "completed",
  "agent_logs": [
    {
      "agent_name": "knowledge_agent",
      "agent_type": "knowledge_agent",
      "start_time": "2026-06-06T10:00:00.000",
      "end_time": "2026-06-06T10:00:00.600",
      "duration_ms": 600.0,
      "status": "completed"
    }
  ],
  "total_duration_ms": 600.0
}
```

### 场景 2: 需要转人工（完整流程）

```
用户: 支付成功但订单没生成
    ↓
KnowledgeAgent: 抱歉，我无法回答这个问题
    ↓
need_human = True
    ↓
TicketClassificationAgent: ticket_type = "technical"
    ↓
PriorityAnalyzerAgent: priority = "high"
    ↓
TicketCreationAgent: ticket_id = 12345
    ↓
DispatchAgent: assignee_id = 101
    ↓
END
```

**执行日志：**

```json
{
  "trace_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "need_human": true,
  "ticket_type": "technical",
  "ticket_priority": "high",
  "ticket_id": 12345,
  "assignee_id": 101,
  "status": "completed",
  "agent_logs": [
    {
      "agent_name": "knowledge_agent",
      "duration_ms": 300.0,
      "status": "completed"
    },
    {
      "agent_name": "ticket_classifier",
      "duration_ms": 400.0,
      "status": "completed"
    },
    {
      "agent_name": "priority_analyzer",
      "duration_ms": 300.0,
      "status": "completed"
    },
    {
      "agent_name": "ticket_creator",
      "duration_ms": 500.0,
      "status": "completed"
    },
    {
      "agent_name": "dispatcher",
      "duration_ms": 200.0,
      "status": "completed"
    }
  ],
  "total_duration_ms": 1700.0
}
```

---

## 5. 使用示例

### 5.1 直接使用 SmartDeskGraph

```python
from app.ai.schemas import AgentState
from app.ai.workflows.smartdesk_graph import smartdesk_graph

# 创建初始状态
state = AgentState(
    user_input="退款多久到账？",
    user_id=1,
    conversation_id="chat_001",
)

# 执行工作流
result = await smartdesk_graph.invoke(state)

# 检查结果
print(f"answer: {result.answer}")
print(f"need_human: {result.need_human}")
print(f"total_duration: {result.get_total_duration_ms()}ms")
```

### 5.2 使用 SupervisorAgent（兼容接口）

```python
from app.ai.agents.supervisor import supervisor_agent

# 方式 1: 使用 run 方法（新接口）
state = AgentState(
    user_input="支付成功但订单没生成",
    user_id=2,
    conversation_id="chat_002",
)
result = await supervisor_agent.run(state)

# 方式 2: 使用 invoke 方法（兼容旧接口）
json_result = await supervisor_agent.invoke(
    "如何重置密码？",
    user_id=3,
    conversation_id="chat_003",
)
```

### 5.3 在 API 中使用

```python
from fastapi import APIRouter
from app.ai.schemas import AgentState
from app.ai.agents.supervisor import supervisor_agent

router = APIRouter()

@router.post("/chat")
async def chat(user_input: str, user_id: int):
    # 创建初始状态
    state = AgentState(
        user_input=user_input,
        user_id=user_id,
    )

    # 执行 SupervisorAgent
    result = await supervisor_agent.run(state)

    # 返回结果
    return {
        "trace_id": result.trace_id,
        "answer": result.answer,
        "need_human": result.need_human,
        "ticket_type": result.ticket_type,
        "ticket_priority": result.ticket_priority,
        "ticket_id": result.ticket_id,
        "assignee_id": result.assignee_id,
        "agent_logs": result.get_agent_summary(),
    }
```

---

## 6. Agent 日志结构

```python
@dataclass
class AgentLog:
    """Agent 执行日志"""
    agent_name: str                           # Agent 名称
    agent_type: AgentType | None = None       # Agent 类型
    start_time: datetime = ...                # 开始时间
    end_time: datetime | None = None          # 结束时间
    duration_ms: float = 0.0                  # 耗时（毫秒）
    status: str = "pending"                   # 状态
    input_summary: str = ""                   # 输入摘要
    output_summary: str = ""                  # 输出摘要
    error: str | None = None                  # 错误信息
```

---

## 7. 状态字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| trace_id | str | 追踪 ID，唯一标识一次执行 |
| user_input | str | 用户输入 |
| user_id | int | 用户 ID |
| conversation_id | str | 会话 ID |
| answer | str | AI 回答 |
| need_human | bool | 是否需要转人工 |
| transfer_reason | TransferReason | 转人工原因 |
| ticket_type | str | 工单分类 |
| ticket_priority | str | 工单优先级 |
| ticket_id | int | 工单 ID |
| assignee_id | int | 分配的客服 ID |
| status | TaskStatus | 任务状态 |
| agent_logs | list[AgentLog] | Agent 执行日志 |
| current_agent | str | 当前执行的 Agent |

---

## 8. 执行时序图

```
┌─────────┐    ┌───────────────┐    ┌──────────────────┐
│  User   │    │ SmartDeskGraph│    │ KnowledgeAgent   │
└────┬────┘    └───────┬───────┘    └────────┬─────────┘
     │                 │                      │
     │  user_input     │                      │
     │────────────────>│                      │
     │                 │                      │
     │                 │    run(state)         │
     │                 │─────────────────────>│
     │                 │                      │
     │                 │    state             │
     │                 │    need_human=True   │
     │                 │<─────────────────────│
     │                 │                      │
     │                 │    ┌─────────────────────────────┐
     │                 │    │ TicketClassificationAgent   │
     │                 │    └──────────────┬──────────────┘
     │                 │    run(state)      │
     │                 │──────────────────>│
     │                 │    state          │
     │                 │    ticket_type=X  │
     │                 │<──────────────────│
     │                 │                   │
     │                 │    ┌─────────────────────────────┐
     │                 │    │ PriorityAnalyzerAgent       │
     │                 │    └──────────────┬──────────────┘
     │                 │    run(state)      │
     │                 │──────────────────>│
     │                 │    state          │
     │                 │    priority=X     │
     │                 │<──────────────────│
     │                 │                   │
     │                 │    ┌─────────────────────────────┐
     │                 │    │ TicketCreationAgent         │
     │                 │    └──────────────┬──────────────┘
     │                 │    run(state)      │
     │                 │──────────────────>│
     │                 │    state          │
     │                 │    ticket_id=X    │
     │                 │<──────────────────│
     │                 │                   │
     │                 │    ┌─────────────────────────────┐
     │                 │    │ DispatchAgent               │
     │                 │    └──────────────┬──────────────┘
     │                 │    run(state)      │
     │                 │──────────────────>│
     │                 │    state          │
     │                 │    assignee_id=X  │
     │                 │<──────────────────│
     │                 │                   │
     │  完整结果       │                   │
     │<────────────────│                   │
     │                 │                   │
```

---

## 9. 错误处理

### 9.1 节点错误

```python
async def knowledge_node(state: AgentState) -> dict:
    try:
        # 执行逻辑
        state = await agent.run(state)
        state.complete_agent(output_summary=state.answer[:200])
    except Exception as e:
        state.fail_agent(str(e))
        raise  # 重新抛出，由图处理
```

### 9.2 图级别错误

```python
async def invoke(self, state: AgentState) -> AgentState:
    try:
        result = await self._graph.ainvoke(state)
        state.status = TaskStatus.COMPLETED
    except Exception as e:
        state.status = TaskStatus.FAILED
        state.error = str(e)
    return state
```

---

## 10. 性能优化

### 10.1 并行执行（未来扩展）

当前实现是串行执行，未来可以考虑：
- 分类和优先级分析并行执行
- 使用 LangGraph 的 parallel 功能

### 10.2 缓存

- 知识库检索结果缓存
- LLM 响应缓存

---

## 11. 监控和调试

### 11.1 trace_id

每次执行都会生成唯一的 `trace_id`，用于：
- 追踪完整执行流程
- 日志关联
- 问题排查

### 11.2 Agent 日志

每个 Agent 的执行都会记录：
- 开始时间
- 结束时间
- 耗时
- 状态
- 输入/输出摘要
- 错误信息

### 11.3 日志示例

```json
{
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-06-06T10:00:00.000",
  "agent_logs": [
    {
      "agent_name": "knowledge_agent",
      "start_time": "2026-06-06T10:00:00.000",
      "end_time": "2026-06-06T10:00:00.300",
      "duration_ms": 300.0,
      "status": "completed",
      "input_summary": "支付成功但订单没生成",
      "output_summary": "抱歉，我无法回答这个问题"
    }
  ]
}
```