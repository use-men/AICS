# Tool Calling 架构文档

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     Tool Calling 架构                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                                                │
│  │   Agent     │                                                │
│  └──────┬──────┘                                                │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────┐                                                │
│  │ToolRegistry │ ← 工具注册中心                                  │
│  └──────┬──────┘                                                │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     Tools                               │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  query_ticket_tool    │  查询工单信息                     │   │
│  │  query_order_tool     │  查询订单信息                     │   │
│  │  query_refund_tool    │  查询退款信息                     │   │
│  │  search_knowledge_tool│  搜索知识库                      │   │
│  │  search_web_tool      │  联网搜索                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心组件

### 2.1 BaseTool 基类

```python
class BaseTool(ABC):
    """工具基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        ...

    @property
    @abstractmethod
    def parameters(self) -> list[ToolParameter]:
        """工具参数定义"""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """执行工具"""
        ...

    def get_schema(self) -> dict:
        """获取 JSON Schema（用于 LLM Function Calling）"""
        ...
```

### 2.2 ToolRegistry 工具注册中心

```python
class ToolRegistry:
    """工具注册中心"""

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        ...

    def get(self, name: str) -> BaseTool | None:
        """获取工具"""
        ...

    async def execute(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """执行工具"""
        ...

    def get_schemas(self, tool_names: list[str] | None = None) -> list[dict]:
        """获取工具 Schema"""
        ...

    def list_tools(self) -> list[dict]:
        """列出所有工具"""
        ...
```

### 2.3 ToolParameter 工具参数

```python
@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str                          # 参数名
    type: str                          # 参数类型
    description: str = ""              # 参数描述
    required: bool = True              # 是否必填
    default: Any = None                # 默认值
```

### 2.4 ToolResult 工具结果

```python
@dataclass
class ToolResult:
    """工具执行结果"""
    status: ToolStatus                 # 执行状态
    data: Any = None                   # 返回数据
    error: str | None = None           # 错误信息
    execution_time_ms: float = 0.0     # 执行耗时
    timestamp: datetime = ...          # 时间戳
```

---

## 3. 内置工具

### 3.1 query_ticket_tool — 工单查询

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ticket_id | int | 是 | 工单ID |

**返回数据：**
```json
{
  "ticket_id": 1,
  "ticket_no": "TK000001",
  "title": "退款咨询",
  "status": "processing",
  "status_label": "处理中",
  "priority": "high",
  "priority_label": "高",
  "ticket_type": "refund",
  "type_label": "退款申请",
  "assignee_id": 101,
  "assignee_name": "客服小王",
  "created_at": "2026-06-06T10:00:00"
}
```

### 3.2 query_order_tool — 订单查询

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_no | str | 是 | 订单号 |

**返回数据：**
```json
{
  "order_no": "ORD20260606001",
  "status": "paid",
  "status_label": "已支付",
  "payment_status": "paid",
  "payment_status_label": "已支付",
  "total_amount": 99.00,
  "paid_amount": 99.00,
  "created_at": "2026-06-06T10:00:00",
  "paid_at": "2026-06-06T10:01:00"
}
```

### 3.3 query_refund_tool — 退款查询

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_no | str | 是 | 订单号 |

**返回数据：**
```json
{
  "order_no": "ORD20260606001",
  "has_refund": true,
  "refund_status": "completed",
  "refund_status_label": "退款完成",
  "refund_amount": 99.00,
  "refund_reason": "用户主动申请退款",
  "estimated_arrival": "1-3个工作日"
}
```

### 3.4 search_knowledge_tool — 知识库搜索

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | str | 是 | 搜索关键词 |
| top_k | int | 否 | 返回结果数量（默认5） |

**返回数据：**
```json
{
  "query": "退款到账时间",
  "total": 3,
  "results": [
    {
      "index": 1,
      "question": "退款多久到账？",
      "answer": "退款将在1-3个工作日到账",
      "score": 0.95
    }
  ]
}
```

### 3.5 search_web_tool — 联网搜索

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | str | 是 | 搜索关键词 |
| max_results | int | 否 | 最大返回结果数（默认5） |

**返回数据：**
```json
{
  "query": "今天天气",
  "total": 3,
  "results": [
    {
      "title": "北京天气预报",
      "url": "https://weather.com/beijing",
      "content": "今天北京晴，气温25-32℃"
    }
  ]
}
```

---

## 4. 使用示例

### 4.1 直接使用工具

```python
from app.ai.tools import query_ticket_tool, search_knowledge_tool

# 查询工单
result = await query_ticket_tool.execute(ticket_id=1)
if result.is_success():
    print(f"工单状态: {result.data['status_label']}")

# 搜索知识库
result = await search_knowledge_tool.execute(query="退款到账时间", top_k=3)
if result.is_success():
    for item in result.data['results']:
        print(f"问题: {item['question']}")
        print(f"回答: {item['answer']}")
```

### 4.2 使用 ToolRegistry

```python
from app.ai.tools import tool_registry

# 执行工具
result = await tool_registry.execute("query_ticket", ticket_id=1)

# 获取工具 Schema
schemas = tool_registry.get_schemas()

# 列出所有工具
tools = tool_registry.list_tools()
```

### 4.3 自定义工具

```python
from app.ai.tools.base import BaseTool, ToolParameter, ToolResult, ToolStatus

class MyCustomTool(BaseTool):
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

# 注册工具
tool_registry.register(MyCustomTool())
```

---

## 5. LLM Function Calling 集成

### 5.1 获取工具 Schema

```python
# 获取所有工具的 Schema
schemas = tool_registry.get_schemas()

# 转换为 OpenAI Function Calling 格式
functions = [
    {
        "name": schema["name"],
        "description": schema["description"],
        "parameters": schema["parameters"],
    }
    for schema in schemas
]
```

### 5.2 在 Agent 中使用

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

response = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "查询工单123的状态"}],
    functions=functions,
    function_call="auto",
)

# 解析 LLM 返回的函数调用
if response.choices[0].message.function_call:
    func_name = response.choices[0].message.function_call.name
    func_args = json.loads(response.choices[0].message.function_call.arguments)

    # 执行工具
    result = await tool_registry.execute(func_name, **func_args)
```

---

## 6. 文件结构

```
backend/app/ai/tools/
├── __init__.py              # 导出所有工具
├── base.py                  # BaseTool 基类 + ToolRegistry
├── query_ticket.py          # 工单查询工具
├── query_order.py           # 订单查询工具
├── query_refund.py          # 退款查询工具
├── search_knowledge.py      # 知识库搜索工具
├── search_web.py            # 联网搜索工具
└── web_search.py            # 旧版联网搜索（兼容）
```

---

## 7. 执行流程

```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────┐
│  Agent  │    │ToolRegistry │    │   Tool      │    │  外部   │
└────┬────┘    └──────┬──────┘    └──────┬──────┘    └────┬────┘
     │                │                   │                │
     │  execute()     │                   │                │
     │───────────────>│                   │                │
     │                │                   │                │
     │                │  get(tool_name)   │                │
     │                │──────────────────>│                │
     │                │                   │                │
     │                │  tool             │                │
     │                │<──────────────────│                │
     │                │                   │                │
     │                │  execute(**kwargs)│                │
     │                │──────────────────>│                │
     │                │                   │                │
     │                │                   │  查询/搜索     │
     │                │                   │───────────────>│
     │                │                   │                │
     │                │                   │  结果          │
     │                │                   │<───────────────│
     │                │                   │                │
     │                │  ToolResult       │                │
     │                │<──────────────────│                │
     │                │                   │                │
     │  ToolResult    │                   │                │
     │<───────────────│                   │                │
     │                │                   │                │
```

---

## 8. 错误处理

### 8.1 工具执行错误

```python
result = await tool_registry.execute("query_ticket", ticket_id=999)

if not result.is_success():
    print(f"错误: {result.error}")
    # 输出: 错误: 工单不存在: 999
```

### 8.2 工具不存在

```python
try:
    result = await tool_registry.execute("nonexistent_tool")
except KeyError as e:
    print(f"工具不存在: {e}")
```

### 8.3 参数缺失

```python
result = await query_ticket_tool.execute()  # 缺少 ticket_id

if not result.is_success():
    print(f"错误: {result.error}")
    # 输出: 错误: 缺少必填参数: ticket_id
```

---

## 9. 扩展指南

### 9.1 添加新工具

1. 创建新文件 `backend/app/ai/tools/my_tool.py`
2. 继承 `BaseTool` 基类
3. 实现 `name`, `description`, `parameters`, `execute` 属性/方法
4. 在 `__init__.py` 中注册

### 9.2 工具分类

| 分类 | 工具 | 说明 |
|------|------|------|
| 查询类 | query_ticket, query_order, query_refund | 查询系统数据 |
| 搜索类 | search_knowledge, search_web | 搜索信息 |
| 操作类 | （未来扩展） | 执行操作 |

---

## 10. 性能优化

### 10.1 缓存

- 知识库搜索结果缓存
- 工单/订单查询结果缓存（短时间）

### 10.2 并发执行

```python
# 并发执行多个工具
import asyncio

results = await asyncio.gather(
    tool_registry.execute("query_ticket", ticket_id=1),
    tool_registry.execute("query_order", order_no="ORD001"),
    tool_registry.execute("search_knowledge", query="退款"),
)
```