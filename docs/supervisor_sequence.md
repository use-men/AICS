# SupervisorAgent 执行时序图

## 1. 问题已解决（不需要转人工）

```
┌─────────┐    ┌───────────────┐    ┌──────────────────┐
│  User   │    │ SupervisorAgent│    │ KnowledgeAgent   │
└────┬────┘    └───────┬───────┘    └────────┬─────────┘
     │                 │                      │
     │  user_input     │                      │
     │────────────────>│                      │
     │                 │                      │
     │                 │    run(state)         │
     │                 │─────────────────────>│
     │                 │                      │
     │                 │                      │ 1. 检索知识库
     │                 │                      │ 2. 检索置信度
     │                 │                      │ 3. 生成回答
     │                 │                      │
     │                 │    state             │
     │                 │<─────────────────────│
     │                 │                      │
     │                 │  need_human=False    │
     │                 │  直接返回            │
     │                 │                      │
     │  answer         │                      │
     │<────────────────│                      │
     │                 │                      │
```

**执行时间线：**

| 时间 | Agent | 操作 | 耗时 |
|------|-------|------|------|
| T0 | Supervisor | 开始调度 | - |
| T1 | KnowledgeAgent | 开始执行 | - |
| T2 | KnowledgeAgent | 检索知识库 | ~100ms |
| T3 | KnowledgeAgent | 生成回答 | ~500ms |
| T4 | KnowledgeAgent | 完成 | ~600ms |
| T5 | Supervisor | 返回结果 | ~600ms |

**Agent 日志：**

```json
{
  "agent_logs": [
    {
      "agent_name": "knowledge_agent",
      "agent_type": "knowledge_agent",
      "start_time": "2026-06-06T10:00:00.000",
      "end_time": "2026-06-06T10:00:00.600",
      "duration_ms": 600.0,
      "status": "completed",
      "input_summary": "退款多久到账？",
      "output_summary": "根据平台规则，退款将在1-3个工作日到账。"
    }
  ],
  "total_duration_ms": 600.0
}
```

---

## 2. 需要转人工（完整流程）

```
┌─────────┐    ┌───────────────┐    ┌──────────────────┐
│  User   │    │ SupervisorAgent│    │ KnowledgeAgent   │
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
     │                 │                      │
     │                 │    ┌─────────────────────────────┐
     │                 │    │ TicketClassificationAgent   │
     │                 │    └──────────────┬──────────────┘
     │                 │                   │
     │                 │    run(state)      │
     │                 │──────────────────>│
     │                 │                   │
     │                 │    state          │
     │                 │    ticket_type=X  │
     │                 │<──────────────────│
     │                 │                   │
     │                 │    ┌─────────────────────────────┐
     │                 │    │ PriorityAnalyzerAgent       │
     │                 │    └──────────────┬──────────────┘
     │                 │                   │
     │                 │    run(state)      │
     │                 │──────────────────>│
     │                 │                   │
     │                 │    state          │
     │                 │    priority=X     │
     │                 │<──────────────────│
     │                 │                   │
     │                 │    ┌─────────────────────────────┐
     │                 │    │ TicketCreationAgent         │
     │                 │    └──────────────┬──────────────┘
     │                 │                   │
     │                 │    run(state)      │
     │                 │──────────────────>│
     │                 │                   │
     │                 │    state          │
     │                 │    ticket_id=X    │
     │                 │<──────────────────│
     │                 │                   │
     │                 │    ┌─────────────────────────────┐
     │                 │    │ DispatchAgent               │
     │                 │    └──────────────┬──────────────┘
     │                 │                   │
     │                 │    run(state)      │
     │                 │──────────────────>│
     │                 │                   │
     │                 │    state          │
     │                 │    assignee_id=X  │
     │                 │<──────────────────│
     │                 │                   │
     │  完整结果       │                   │
     │<────────────────│                   │
     │                 │                   │
```

**执行时间线：**

| 时间 | Agent | 操作 | 耗时 |
|------|-------|------|------|
| T0 | Supervisor | 开始调度 | - |
| T1 | KnowledgeAgent | 开始执行 | - |
| T2 | KnowledgeAgent | 检索知识库 | ~100ms |
| T3 | KnowledgeAgent | 置信度低，需要转人工 | ~200ms |
| T4 | KnowledgeAgent | 完成 | ~300ms |
| T5 | TicketClassificationAgent | 开始执行 | - |
| T6 | TicketClassificationAgent | 分类完成 | ~400ms |
| T7 | PriorityAnalyzerAgent | 开始执行 | - |
| T8 | PriorityAnalyzerAgent | 优先级分析完成 | ~300ms |
| T9 | TicketCreationAgent | 开始执行 | - |
| T10 | TicketCreationAgent | 创建工单完成 | ~500ms |
| T11 | DispatchAgent | 开始执行 | - |
| T12 | DispatchAgent | 派单完成 | ~200ms |
| T13 | Supervisor | 返回完整结果 | ~1700ms |

**Agent 日志：**

```json
{
  "agent_logs": [
    {
      "agent_name": "knowledge_agent",
      "agent_type": "knowledge_agent",
      "start_time": "2026-06-06T10:00:00.000",
      "end_time": "2026-06-06T10:00:00.300",
      "duration_ms": 300.0,
      "status": "completed",
      "input_summary": "支付成功但订单没生成",
      "output_summary": "抱歉，我无法回答这个问题"
    },
    {
      "agent_name": "ticket_classifier",
      "agent_type": "ticket_classifier",
      "start_time": "2026-06-06T10:00:00.300",
      "end_time": "2026-06-06T10:00:00.700",
      "duration_ms": 400.0,
      "status": "completed",
      "input_summary": "{\"title\": \"支付成功但订单没生成\", ...}",
      "output_summary": "ticket_type: technical"
    },
    {
      "agent_name": "priority_analyzer",
      "agent_type": "priority_analyzer",
      "start_time": "2026-06-06T10:00:00.700",
      "end_time": "2026-06-06T10:00:01.000",
      "duration_ms": 300.0,
      "status": "completed",
      "input_summary": "{\"title\": \"支付成功但订单没生成\", ...}",
      "output_summary": "priority: high"
    },
    {
      "agent_name": "ticket_creator",
      "agent_type": "ticket_creator",
      "start_time": "2026-06-06T10:00:01.000",
      "end_time": "2026-06-06T10:00:01.500",
      "duration_ms": 500.0,
      "status": "completed",
      "input_summary": "支付成功但订单没生成",
      "output_summary": "ticket_no: TK000001"
    },
    {
      "agent_name": "dispatcher",
      "agent_type": "dispatcher",
      "start_time": "2026-06-06T10:00:01.500",
      "end_time": "2026-06-06T10:00:01.700",
      "duration_ms": 200.0,
      "status": "completed",
      "input_summary": "type=technical, priority=high",
      "output_summary": "assignee_id: 101"
    }
  ],
  "total_duration_ms": 1700.0
}
```

---

## 3. 错误处理流程

```
┌─────────┐    ┌───────────────┐    ┌──────────────────┐
│  User   │    │ SupervisorAgent│    │ KnowledgeAgent   │
└────┬────┘    └───────┬───────┘    └────────┬─────────┘
     │                 │                      │
     │  user_input     │                      │
     │────────────────>│                      │
     │                 │                      │
     │                 │    run(state)         │
     │                 │─────────────────────>│
     │                 │                      │
     │                 │    Exception          │
     │                 │<─────────────────────│
     │                 │                      │
     │                 │  记录错误日志         │
     │                 │  设置 status=FAILED   │
     │                 │                      │
     │  错误响应       │                      │
     │<────────────────│                      │
     │                 │                      │
```

**错误日志：**

```json
{
  "agent_logs": [
    {
      "agent_name": "knowledge_agent",
      "agent_type": "knowledge_agent",
      "start_time": "2026-06-06T10:00:00.000",
      "end_time": "2026-06-06T10:00:00.100",
      "duration_ms": 100.0,
      "status": "failed",
      "input_summary": "测试输入",
      "output_summary": "",
      "error": "知识库服务不可用"
    }
  ],
  "total_duration_ms": 100.0
}
```

---

## 4. 核心流程伪代码

```python
async def run(state: AgentState) -> AgentState:
    """
    统一执行入口
    """
    state.status = TaskStatus.PROCESSING

    try:
        # 1. 调用 KnowledgeAgent
        state = await self._run_knowledge_agent(state)

        # 2. 判断是否需要转人工
        if not state.need_human:
            state.status = TaskStatus.COMPLETED
            return state

        # 3. 需要转人工，依次调用子 Agent
        state = await self._run_classification_agent(state)  # 工单分类
        state = await self._run_priority_agent(state)        # 优先级分析
        state = await self._run_ticket_creator_agent(state)  # 创建工单
        state = await self._run_dispatch_agent(state)        # 智能派单

        state.status = TaskStatus.COMPLETED

    except Exception as e:
        state.error = str(e)
        state.status = TaskStatus.FAILED

    return state
```

---

## 5. Agent 日志数据结构

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

## 6. 状态流转图

```
┌─────────────────────────────────────────────────────────────┐
│                    SupervisorAgent 状态流转                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PENDING                                                    │
│     ↓                                                       │
│  PROCESSING                                                 │
│     ↓                                                       │
│  ┌─────────────────────────────────────────┐               │
│  │           KnowledgeAgent                │               │
│  └─────────────────┬───────────────────────┘               │
│                    ↓                                       │
│         ┌─────────────────────┐                           │
│         │ need_human == True? │                           │
│         └─────────┬───────────┘                           │
│                   │                                        │
│        ┌──────────┴──────────┐                            │
│        ↓                     ↓                            │
│   ┌─────────┐          ┌──────────┐                      │
│   │   No    │          │   Yes    │                      │
│   └────┬────┘          └────┬─────┘                      │
│        │                    │                             │
│        ↓                    ↓                             │
│   ┌─────────┐    ┌─────────────────────┐                 │
│   │COMPLETED│    │ ClassificationAgent │                 │
│   └─────────┘    └──────────┬──────────┘                 │
│                             ↓                            │
│                    ┌────────────────┐                    │
│                    │PriorityAgent   │                    │
│                    └────────┬───────┘                    │
│                             ↓                            │
│                    ┌────────────────┐                    │
│                    │TicketCreator   │                    │
│                    └────────┬───────┘                    │
│                             ↓                            │
│                    ┌────────────────┐                    │
│                    │DispatchAgent   │                    │
│                    └────────┬───────┘                    │
│                             ↓                            │
│                       ┌─────────┐                        │
│                       │COMPLETED│                        │
│                       └─────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```