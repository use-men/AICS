"""
ToolCallingAgent — Tool Calling Agent。

职责:
    1. 分析用户问题，判断是否需要调用工具
    2. 如果需要，调用相应的工具
    3. 将工具结果写入 state.metadata
    4. 生成最终回答

流程:
    用户问题 → LLM 分析 → 判断是否需要工具 → 调用工具 → 生成回答
"""

import json
import logging
import re
from typing import Any

from app.ai.agents.base import BaseAgent
from app.ai.schemas import AgentState, AgentType, TaskStatus, ToolLog
from app.ai.tools import tool_registry

logger = logging.getLogger(__name__)


# ============================================================
#  工具调用规则（严格匹配）
# ============================================================


# 工单号格式：TK + 6位数字，如 TK000001, TK123456
TICKET_PATTERN = re.compile(r"(?:工单[号编号]?\s*[：:]*\s*|TK)(\d{6,})")

# 订单号格式：ORD + 6位以上数字，或纯数字订单号（8位以上）
ORDER_PATTERN = re.compile(r"(?:订单[号编号]?\s*[：:]*\s*|ORD)?(\d{8,}|ORD\d{6,})")


def _validate_ticket_id(value: str) -> int | None:
    """验证并转换工单号"""
    try:
        ticket_id = int(value)
        # 工单号通常是 1-999999 的整数
        if 1 <= ticket_id <= 999999:
            return ticket_id
    except ValueError:
        pass
    return None


def _validate_order_no(value: str) -> str | None:
    """验证订单号格式"""
    # 订单号格式：ORD123456 或 纯数字（8位以上）
    if re.match(r"^ORD\d{6,}$", value):
        return value
    if re.match(r"^\d{8,}$", value):
        return value
    return None


TOOL_RULES = [
    {
        "tool_name": "query_ticket",
        "patterns": [
            r"工单[号编号]?\s*[：:]*\s*(\d{6,})",
            r"(?:查询|查看|搜索)\s*工单\s*(?:TK)?(\d{6,})",
            r"工单\s*(?:TK)?(\d{6,})\s*(?:的|状态|信息|情况)",
            r"TK(\d{6,})",
        ],
        "param_name": "ticket_id",
        "param_type": "int",
        "description": "查询工单信息",
        "validator": _validate_ticket_id,
    },
    {
        "tool_name": "query_order",
        "patterns": [
            r"订单[号编号]?\s*[：:]*\s*(ORD\d{6,}|\d{8,})",
            r"(?:查询|查看|搜索)\s*订单\s*(ORD\d{6,}|\d{8,})",
            r"订单\s*(ORD\d{6,}|\d{8,})\s*(?:的|状态|信息|情况)",
            r"(ORD\d{6,})",
        ],
        "param_name": "order_no",
        "param_type": "str",
        "description": "查询订单信息",
        "validator": _validate_order_no,
    },
    {
        "tool_name": "query_refund",
        "patterns": [
            r"退款[号编号]?\s*[：:]*\s*(ORD\d{6,}|\d{8,})",
            r"(?:查询|查看|搜索)\s*退款\s*(ORD\d{6,}|\d{8,})",
            r"订单\s*(ORD\d{6,}|\d{8,})\s*的\s*退款",
            r"退款\s*(?:状态|进度|到账)",
        ],
        "param_name": "order_no",
        "param_type": "str",
        "description": "查询退款信息",
        "requires_param": False,
    },
    {
        "tool_name": "search_knowledge",
        "patterns": [
            r"(?:搜索|查询|查找)\s*知识库",
            r"知识库\s*(?:中|里)?\s*(?:有|关于)",
        ],
        "param_name": "query",
        "param_type": "str",
        "description": "搜索知识库",
        "use_user_input": True,
    },
    {
        "tool_name": "search_web",
        "patterns": [
            r"(?:搜索|查询|查找)\s*(?:互联网|网络|网上|网页)",
            r"帮我\s*(?:搜|查)\s*(?:一下|下)",
            r"最新\s*(?:的|消息|信息|新闻)",
        ],
        "param_name": "query",
        "param_type": "str",
        "description": "联网搜索",
        "use_user_input": True,
    },
]


# ============================================================
#  ToolCallingAgent
# ============================================================


class ToolCallingAgent(BaseAgent):
    """
    Tool Calling Agent。

    分析用户问题，判断是否需要调用工具，并执行工具调用。
    """

    @property
    def agent_name(self) -> str:
        return "tool_calling"

    @property
    def agent_type(self) -> AgentType:
        return AgentType.TOOL_CALLING

    @property
    def system_prompt(self) -> str:
        return """你是一个智能助手，负责分析用户问题并决定是否需要调用工具。

## 工具列表
{tools_description}

## 判断规则
1. 如果用户问题包含订单号、工单号等具体信息，应该调用相应工具查询
2. 如果用户询问退款相关问题，应该调用退款查询工具
3. 如果用户需要搜索知识库或互联网，应该调用相应搜索工具
4. 如果问题可以直接回答，不需要调用工具

## 输出格式
请以 JSON 格式输出你的判断：
```json
{{
    "need_tool": true/false,
    "tool_name": "工具名称（如果需要工具）",
    "tool_params": {{"参数名": "参数值"}},
    "reason": "判断原因"
}}
```
"""

    @property
    def _temperature(self) -> float:
        return 0.1  # 低温度，保证判断稳定

    # ---- 核心接口 ----

    async def run(self, state: AgentState) -> AgentState:
        """
        执行 Tool Calling。

        Args:
            state: 当前 Agent 状态

        Returns:
            更新后的 Agent 状态
        """
        state.agent_type = self.agent_type
        state.status = TaskStatus.PROCESSING

        logger.info("[ToolCalling] 开始分析 | trace_id: %s | user_input: %s",
                    state.trace_id, state.user_input[:100])

        try:
            # 1. 使用规则匹配判断是否需要工具
            tool_decision = self._match_tool_rules(state.user_input)

            # 2. 如果规则匹配失败，使用 LLM 判断
            if not tool_decision:
                tool_decision = await self._llm_analyze(state)

            # 3. 如果需要工具，执行工具调用
            if tool_decision and tool_decision.get("need_tool"):
                tool_name = tool_decision.get("tool_name")
                tool_params = tool_decision.get("tool_params", {})

                logger.info("[ToolCalling] 需要调用工具: %s | params: %s", tool_name, tool_params)

                # 执行工具
                tool_result = await self._execute_tool(state, tool_name, tool_params)

                # 将工具结果写入 metadata
                if tool_result:
                    state.metadata["tool_results"] = state.metadata.get("tool_results", {})
                    state.metadata["tool_results"][tool_name] = tool_result

            state.status = TaskStatus.COMPLETED

        except Exception as e:
            logger.error("[ToolCalling] 分析失败: %s", e)
            state.error = str(e)
            state.status = TaskStatus.FAILED

        logger.info("[ToolCalling] 分析完成 | trace_id: %s | tool_logs: %d",
                    state.trace_id, len(state.tool_logs))

        return state

    # ---- 规则匹配 ----

    def _match_tool_rules(self, user_input: str) -> dict | None:
        """
        使用规则匹配判断是否需要工具。

        Args:
            user_input: 用户输入

        Returns:
            工具决策字典，或 None
        """
        for rule in TOOL_RULES:
            for pattern in rule["patterns"]:
                match = re.search(pattern, user_input)
                if match:
                    # 提取参数
                    tool_params = {}

                    if rule.get("use_user_input"):
                        # 使用用户输入作为参数
                        tool_params[rule["param_name"]] = user_input
                    elif match.groups():
                        # 从正则匹配中提取参数
                        param_value = match.group(1)

                        # 验证参数
                        validator = rule.get("validator")
                        if validator:
                            validated_value = validator(param_value)
                            if validated_value is None:
                                # 验证失败，跳过这个匹配
                                logger.debug("[ToolCalling] 参数验证失败: %s", param_value)
                                continue
                            param_value = validated_value
                        elif rule["param_type"] == "int":
                            try:
                                param_value = int(param_value)
                            except ValueError:
                                continue

                        tool_params[rule["param_name"]] = param_value
                    elif not rule.get("requires_param", True):
                        # 不需要参数的工具
                        pass
                    else:
                        continue

                    logger.info("[ToolCalling] 规则匹配成功: %s | params: %s",
                               rule["tool_name"], tool_params)

                    return {
                        "need_tool": True,
                        "tool_name": rule["tool_name"],
                        "tool_params": tool_params,
                        "reason": f"规则匹配: {rule['description']}",
                    }

        return None

    # ---- LLM 分析 ----

    async def _llm_analyze(self, state: AgentState) -> dict | None:
        """
        使用 LLM 分析是否需要工具。

        Args:
            state: 当前 Agent 状态

        Returns:
            工具决策字典，或 None
        """
        try:
            # 构建工具描述
            tools_description = "\n".join([
                f"- {tool['name']}: {tool['description']}"
                for tool in tool_registry.list_tools()
            ])

            # 构建 Prompt
            prompt = self.system_prompt.format(tools_description=tools_description)

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": state.user_input},
            ]

            # 调用 LLM
            response = await self.llm.ainvoke(messages)
            result = self._parse_llm_response(response.content)

            if result and result.get("need_tool"):
                logger.info("[ToolCalling] LLM 判断需要工具: %s", result.get("tool_name"))
                return result

            return None

        except Exception as e:
            logger.warning("[ToolCalling] LLM 分析失败: %s", e)
            return None

    def _parse_llm_response(self, raw: str) -> dict | None:
        """解析 LLM 返回的 JSON"""
        try:
            text = raw.strip()
            # 处理可能被 markdown 包裹的情况
            if "```" in text:
                # 提取 JSON 部分
                json_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
                if json_match:
                    text = json_match.group(1).strip()

            result = json.loads(text)

            # 校验字段
            if not isinstance(result, dict):
                return None

            if "need_tool" not in result:
                return None

            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("[ToolCalling] JSON 解析失败: %s", e)
            return None

    # ---- 工具执行 ----

    async def _execute_tool(self, state: AgentState, tool_name: str, tool_params: dict) -> Any:
        """
        执行工具调用。

        Args:
            state: 当前 Agent 状态
            tool_name: 工具名称
            tool_params: 工具参数

        Returns:
            工具执行结果
        """
        # 开始记录日志
        log = state.start_tool(tool_name, tool_params)

        try:
            # 执行工具
            result = await tool_registry.execute(tool_name, **tool_params)

            if result.is_success():
                log.complete(result.data)
                logger.info("[ToolCalling] 工具执行成功: %s", tool_name)
                return result.data
            else:
                log.fail(result.error)
                logger.warning("[ToolCalling] 工具执行失败: %s | error: %s", tool_name, result.error)
                return None

        except Exception as e:
            log.fail(str(e))
            logger.error("[ToolCalling] 工具执行异常: %s | error: %s", tool_name, e)
            return None

    # ---- 兼容旧接口 ----

    async def invoke(self, input_text: str, **kwargs: Any) -> str:
        """兼容旧接口"""
        state = self._create_state(input_text, **kwargs)
        state = await self.run(state)

        return json.dumps({
            "tool_logs": state.get_tool_summary(),
            "metadata": state.metadata.get("tool_results", {}),
        }, ensure_ascii=False)

    async def stream(self, input_text: str, **kwargs: Any):
        """兼容旧接口"""
        result = await self.invoke(input_text, **kwargs)
        yield result


# ---- 全局单例 ----

tool_calling_agent = ToolCallingAgent()