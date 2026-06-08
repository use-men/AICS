"""
ToolCallingAgent 工具匹配逻辑单元测试。

测试：
1. 正常匹配：查询订单 ORD123456
2. 正常匹配：查询工单 TK000001
3. 不触发：支付成功但是订单没生成
4. 不触发：订单有问题
5. 不触发：订单怎么还没发货
"""

import pytest
from app.ai.agents.tool_calling import (
    ToolCallingAgent,
    _validate_ticket_id,
    _validate_order_no,
    TICKET_PATTERN,
    ORDER_PATTERN,
)


class TestTicketValidation:
    """工单号验证测试"""

    def test_valid_ticket_id(self):
        """测试有效工单号"""
        assert _validate_ticket_id("1") == 1
        assert _validate_ticket_id("123") == 123
        assert _validate_ticket_id("123456") == 123456

    def test_invalid_ticket_id(self):
        """测试无效工单号"""
        assert _validate_ticket_id("abc") is None
        assert _validate_ticket_id("0") is None  # 0 不是有效工单号
        assert _validate_ticket_id("ORD123") is None  # 订单号格式


class TestOrderValidation:
    """订单号验证测试"""

    def test_valid_order_no_ord(self):
        """测试有效订单号（ORD格式）"""
        assert _validate_order_no("ORD123456") == "ORD123456"
        assert _validate_order_no("ORD20250607001") == "ORD20250607001"

    def test_valid_order_no_numeric(self):
        """测试有效订单号（纯数字格式）"""
        assert _validate_order_no("12345678") == "12345678"
        assert _validate_order_no("1234567890123") == "1234567890123"

    def test_invalid_order_no(self):
        """测试无效订单号"""
        assert _validate_order_no("abc") is None
        assert _validate_order_no("1234567") is None  # 少于8位
        assert _validate_order_no("ORD123") is None  # ORD后少于6位
        assert _validate_order_no("没生成") is None  # 中文
        assert _validate_order_no("有问题") is None  # 中文


class TestTicketPattern:
    """工单号正则匹配测试"""

    def test_match_ticket_no_prefix(self):
        """匹配：工单号123456（6位数字）"""
        match = TICKET_PATTERN.search("工单号123456")
        assert match is not None
        assert match.group(1) == "123456"

    def test_match_ticket_tk_prefix(self):
        """匹配：TK000001"""
        match = TICKET_PATTERN.search("TK000001")
        assert match is not None
        assert match.group(1) == "000001"

    def test_match_ticket_query(self):
        """匹配：查询工单 TK123456"""
        match = TICKET_PATTERN.search("查询工单 TK123456")
        assert match is not None
        assert match.group(1) == "123456"

    def test_no_match(self):
        """不匹配：普通文本"""
        assert TICKET_PATTERN.search("支付成功但是订单没生成") is None
        assert TICKET_PATTERN.search("订单有问题") is None

    def test_no_match_short_number(self):
        """不匹配：位数不足的数字"""
        assert TICKET_PATTERN.search("工单号123") is None
        assert TICKET_PATTERN.search("工单 123") is None


class TestOrderPattern:
    """订单号正则匹配测试"""

    def test_match_order_ord(self):
        """匹配：ORD123456"""
        match = ORDER_PATTERN.search("ORD123456")
        assert match is not None
        assert match.group(1) == "ORD123456"

    def test_match_order_numeric(self):
        """匹配：12345678（8位数字）"""
        match = ORDER_PATTERN.search("12345678")
        assert match is not None
        assert match.group(1) == "12345678"

    def test_match_order_query(self):
        """匹配：查询订单 ORD123456"""
        match = ORDER_PATTERN.search("查询订单 ORD123456")
        assert match is not None
        assert match.group(1) == "ORD123456"

    def test_no_match_chinese(self):
        """不匹配：中文文本"""
        assert ORDER_PATTERN.search("支付成功但是订单没生成") is None
        assert ORDER_PATTERN.search("订单有问题") is None
        assert ORDER_PATTERN.search("订单怎么还没发货") is None
        assert ORDER_PATTERN.search("没生成") is None

    def test_no_match_short_number(self):
        """不匹配：位数不足的数字"""
        assert ORDER_PATTERN.search("订单 1234567") is None  # 7位
        assert ORDER_PATTERN.search("订单 123456") is None  # 6位


class TestToolCallingAgent:
    """ToolCallingAgent 工具匹配测试"""

    def setup_method(self):
        """测试前初始化"""
        self.agent = ToolCallingAgent()

    def test_match_query_ticket(self):
        """测试匹配：查询工单 TK000001"""
        result = self.agent._match_tool_rules("查询工单 TK000001")
        assert result is not None
        assert result["need_tool"] is True
        assert result["tool_name"] == "query_ticket"
        assert result["tool_params"]["ticket_id"] == 1

    def test_match_query_order(self):
        """测试匹配：查询订单 ORD123456"""
        result = self.agent._match_tool_rules("查询订单 ORD123456")
        assert result is not None
        assert result["need_tool"] is True
        assert result["tool_name"] == "query_order"
        assert result["tool_params"]["order_no"] == "ORD123456"

    def test_no_match_payment_success(self):
        """测试不触发：支付成功但是订单没生成"""
        result = self.agent._match_tool_rules("支付成功但是订单没生成")
        assert result is None

    def test_no_match_order_problem(self):
        """测试不触发：订单有问题"""
        result = self.agent._match_tool_rules("订单有问题")
        assert result is None

    def test_no_match_order_shipping(self):
        """测试不触发：订单怎么还没发货"""
        result = self.agent._match_tool_rules("订单怎么还没发货")
        assert result is None

    def test_match_ticket_with_status(self):
        """测试匹配：工单 TK000001 的状态"""
        result = self.agent._match_tool_rules("工单 TK000001 的状态")
        assert result is not None
        assert result["tool_name"] == "query_ticket"
        assert result["tool_params"]["ticket_id"] == 1

    def test_match_order_with_status(self):
        """测试匹配：订单 ORD123456 的状态"""
        result = self.agent._match_tool_rules("订单 ORD123456 的状态")
        assert result is not None
        assert result["tool_name"] == "query_order"
        assert result["tool_params"]["order_no"] == "ORD123456"

    def test_no_match_short_order(self):
        """测试不触发：订单号太短"""
        result = self.agent._match_tool_rules("订单 1234567")
        assert result is None

    def test_no_match_ticket_short_number(self):
        """测试不触发：工单号位数不足"""
        result = self.agent._match_tool_rules("工单 123")
        # 123 只有3位，不符合6位以上的要求
        assert result is None

    def test_match_ticket_long_number(self):
        """测试匹配：工单号位数足够"""
        result = self.agent._match_tool_rules("工单 123456")
        assert result is not None
        assert result["tool_name"] == "query_ticket"
        assert result["tool_params"]["ticket_id"] == 123456


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
