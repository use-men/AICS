"""
SupervisorAgent 单元测试

测试 SupervisorAgent 的调度逻辑，包括：
1. 知识库回答成功（不需要转人工）
2. 知识库回答失败（需要转人工）
3. 完整的转人工流程
4. Agent 日志记录
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.ai.agents.supervisor import SupervisorAgent
from app.ai.schemas import (
    AgentState,
    AgentLog,
    AgentType,
    TaskStatus,
    TransferReason,
)


# ============================================================
#  Mock Fixtures
# ============================================================


@pytest.fixture
def supervisor():
    """创建 SupervisorAgent 实例"""
    return SupervisorAgent()


@pytest.fixture
def initial_state():
    """创建初始 AgentState"""
    return AgentState(
        user_input="退款多久到账？",
        user_id=1,
        conversation_id="test_chat_001",
    )


# ============================================================
#  测试 1: 知识库回答成功（不需要转人工）
# ============================================================


class TestKnowledgeAgentSuccess:
    """测试知识库回答成功，不需要转人工"""

    @pytest.mark.asyncio
    async def test_knowledge_agent_resolves_issue(self, supervisor, initial_state):
        """问题在知识库中找到答案，不需要转人工"""
        # Mock KnowledgeAgent
        mock_state = AgentState(
            user_input=initial_state.user_input,
            user_id=1,
            conversation_id="test_chat_001",
            answer="根据平台规则，退款将在1-3个工作日到账。",
            need_human=False,
            status=TaskStatus.COMPLETED,
        )

        with patch("app.ai.agents.supervisor.KnowledgeAgent") as MockKA:
            mock_ka = MockKA.return_value
            mock_ka.run = AsyncMock(return_value=mock_state)

            result = await supervisor.run(initial_state)

            # 验证结果
            assert result.need_human is False
            assert result.answer == "根据平台规则，退款将在1-3个工作日到账。"
            assert result.status == TaskStatus.COMPLETED

            # 验证只调用了 KnowledgeAgent
            mock_ka.run.assert_called_once()

            # 验证日志记录
            assert len(result.agent_logs) == 1
            assert result.agent_logs[0].agent_name == "knowledge_agent"
            assert result.agent_logs[0].status == "completed"


# ============================================================
#  测试 2: 需要转人工（完整流程）
# ============================================================


class TestTransferToHuman:
    """测试需要转人工的完整流程"""

    @pytest.mark.asyncio
    async def test_full_transfer_flow(self, supervisor, initial_state):
        """完整转人工流程：分类 → 优先级 → 创建工单 → 派单"""
        # Mock KnowledgeAgent（返回需要转人工）
        knowledge_state = AgentState(
            user_input=initial_state.user_input,
            need_human=True,
            transfer_reason=TransferReason.LOW_CONFIDENCE,
            answer="抱歉，我无法回答这个问题，正在为您转接人工客服。",
            status=TaskStatus.COMPLETED,
        )

        # Mock TicketClassificationAgent
        classification_state = AgentState(
            ticket_type="refund",
            status=TaskStatus.COMPLETED,
        )

        # Mock PriorityAnalyzerAgent
        priority_state = AgentState(
            ticket_priority="high",
            status=TaskStatus.COMPLETED,
        )

        # Mock TicketCreationAgent
        ticket_state = AgentState(
            ticket_id=12345,
            ticket_info=MagicMock(
                ticket_no="TK000001",
                title="退款咨询",
            ),
            status=TaskStatus.COMPLETED,
        )

        # Mock DispatchAgent
        dispatch_state = AgentState(
            assignee_id=101,
            metadata={"assignee_name": "客服小王"},
            status=TaskStatus.COMPLETED,
        )

        with patch("app.ai.agents.supervisor.KnowledgeAgent") as MockKA, \
             patch("app.ai.agents.supervisor.TicketClassificationAgent") as MockTCA, \
             patch("app.ai.agents.supervisor.PriorityAnalyzerAgent") as MockPA, \
             patch("app.ai.agents.supervisor.TicketCreationAgent") as MockTC, \
             patch("app.ai.agents.supervisor.DispatchAgent") as MockDA:

            # 设置 Mock
            MockKA.return_value.run = AsyncMock(return_value=knowledge_state)
            MockTCA.return_value.run = AsyncMock(return_value=classification_state)
            MockTCA.return_value.agent_name = "ticket_classifier"
            MockTCA.return_value.agent_type = AgentType.TICKET_CLASSIFIER
            MockPA.return_value.run = AsyncMock(return_value=priority_state)
            MockPA.return_value.agent_name = "priority_analyzer"
            MockPA.return_value.agent_type = AgentType.PRIORITY_ANALYZER
            MockTC.return_value.run = AsyncMock(return_value=ticket_state)
            MockTC.return_value.agent_name = "ticket_creator"
            MockTC.return_value.agent_type = AgentType.TICKET_CREATOR
            MockDA.return_value.run = AsyncMock(return_value=dispatch_state)
            MockDA.return_value.agent_name = "dispatcher"
            MockDA.return_value.agent_type = AgentType.DISPATCHER

            # 执行
            result = await supervisor.run(initial_state)

            # 验证结果
            assert result.need_human is True
            assert result.ticket_type == "refund"
            assert result.ticket_priority == "high"
            assert result.ticket_id == 12345
            assert result.assignee_id == 101

            # 验证所有 Agent 都被调用
            MockKA.return_value.run.assert_called_once()
            MockTCA.return_value.run.assert_called_once()
            MockPA.return_value.run.assert_called_once()
            MockTC.return_value.run.assert_called_once()
            MockDA.return_value.run.assert_called_once()

            # 验证日志记录（5个Agent）
            assert len(result.agent_logs) == 5
            agent_names = [log.agent_name for log in result.agent_logs]
            assert "knowledge_agent" in agent_names
            assert "ticket_classifier" in agent_names
            assert "priority_analyzer" in agent_names
            assert "ticket_creator" in agent_names
            assert "dispatcher" in agent_names


# ============================================================
#  测试 3: Agent 日志记录
# ============================================================


class TestAgentLogs:
    """测试 Agent 日志记录"""

    @pytest.mark.asyncio
    async def test_agent_logs_timing(self, supervisor, initial_state):
        """验证 Agent 日志的时间记录"""
        mock_state = AgentState(
            answer="测试回答",
            need_human=False,
            status=TaskStatus.COMPLETED,
        )

        with patch("app.ai.agents.supervisor.KnowledgeAgent") as MockKA:
            mock_ka = MockKA.return_value
            mock_ka.run = AsyncMock(return_value=mock_state)

            result = await supervisor.run(initial_state)

            # 验证日志
            assert len(result.agent_logs) == 1
            log = result.agent_logs[0]

            # 验证时间记录
            assert log.start_time is not None
            assert log.end_time is not None
            assert log.duration_ms >= 0
            assert log.status == "completed"

    @pytest.mark.asyncio
    async def test_agent_logs_current_agent(self, supervisor, initial_state):
        """验证 current_agent 字段更新"""
        mock_state = AgentState(
            answer="测试回答",
            need_human=False,
            status=TaskStatus.COMPLETED,
        )

        with patch("app.ai.agents.supervisor.KnowledgeAgent") as MockKA:
            mock_ka = MockKA.return_value
            mock_ka.run = AsyncMock(return_value=mock_state)

            # 执行前
            assert initial_state.current_agent == ""

            result = await supervisor.run(initial_state)

            # 执行后
            assert result.current_agent == ""  # 完成后清空

    @pytest.mark.asyncio
    async def test_agent_logs_on_failure(self, supervisor, initial_state):
        """验证 Agent 失败时的日志记录"""
        with patch("app.ai.agents.supervisor.KnowledgeAgent") as MockKA:
            mock_ka = MockKA.return_value
            mock_ka.run = AsyncMock(side_effect=Exception("知识库服务不可用"))

            result = await supervisor.run(initial_state)

            # 验证失败日志
            assert result.status == TaskStatus.FAILED
            assert result.error is not None
            assert len(result.agent_logs) == 1
            assert result.agent_logs[0].status == "failed"


# ============================================================
#  测试 4: AgentState 日志方法
# ============================================================


class TestAgentStateLogs:
    """测试 AgentState 的日志方法"""

    def test_start_agent(self):
        """测试 start_agent 方法"""
        state = AgentState()
        log = state.start_agent(
            agent_name="test_agent",
            agent_type=AgentType.CUSTOMER_SERVICE,
            input_summary="测试输入",
        )

        assert state.current_agent == "test_agent"
        assert len(state.agent_logs) == 1
        assert log.agent_name == "test_agent"
        assert log.status == "running"

    def test_complete_agent(self):
        """测试 complete_agent 方法"""
        state = AgentState()
        state.start_agent("test_agent")
        state.complete_agent(output_summary="测试输出")

        assert state.current_agent == ""
        assert state.agent_logs[0].status == "completed"
        assert state.agent_logs[0].output_summary == "测试输出"

    def test_fail_agent(self):
        """测试 fail_agent 方法"""
        state = AgentState()
        state.start_agent("test_agent")
        state.fail_agent("测试错误")

        assert state.current_agent == ""
        assert state.agent_logs[0].status == "failed"
        assert state.agent_logs[0].error == "测试错误"

    def test_get_total_duration_ms(self):
        """测试 get_total_duration_ms 方法"""
        state = AgentState()
        state.start_agent("agent1")
        state.complete_agent()
        state.start_agent("agent2")
        state.complete_agent()

        total = state.get_total_duration_ms()
        assert total >= 0

    def test_get_agent_summary(self):
        """测试 get_agent_summary 方法"""
        state = AgentState()
        state.start_agent("agent1", AgentType.CUSTOMER_SERVICE, "input1")
        state.complete_agent("output1")

        summary = state.get_agent_summary()
        assert len(summary) == 1
        assert summary[0]["agent_name"] == "agent1"
        assert summary[0]["status"] == "completed"


# ============================================================
#  测试 5: invoke 兼容接口
# ============================================================


class TestInvokeCompat:
    """测试 invoke 兼容接口"""

    @pytest.mark.asyncio
    async def test_invoke_returns_json(self, supervisor, initial_state):
        """验证 invoke 返回 JSON 字符串"""
        mock_state = AgentState(
            answer="测试回答",
            need_human=False,
            status=TaskStatus.COMPLETED,
        )

        with patch("app.ai.agents.supervisor.KnowledgeAgent") as MockKA:
            MockKA.return_value.run = AsyncMock(return_value=mock_state)

            result = await supervisor.invoke(
                "退款多久到账？",
                user_id=1,
                conversation_id="test_chat_001",
            )

            # 验证返回 JSON
            data = json.loads(result)
            assert "answer" in data
            assert "need_human" in data
            assert "agent_logs" in data
            assert "total_duration_ms" in data


# ============================================================
#  运行测试
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])