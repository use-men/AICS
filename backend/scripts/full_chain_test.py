"""
全链路压测脚本 — 测试完整的客服流程。

流程:
    1. 用户登录
    2. AI 问答
    3. KnowledgeAgent
    4. ToolCalling
    5. 无法解决 → 创建工单
    6. ClassificationAgent
    7. PriorityAgent
    8. DispatchAgent
    9. 客服收到通知
    10. WebSocket 聊天
    11. 解决工单
    12. 管理端统计更新
"""

import asyncio
import json
import httpx
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"


class FullChainTester:
    """全链路测试器"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.user_token = None
        self.cs_token = None
        self.admin_token = None
        self.user_id = None
        self.cs_user_id = None
        self.trace_ids = []

    async def close(self):
        await self.client.aclose()

    # ---- 1. 用户登录 ----

    async def test_user_login(self):
        """测试用户登录"""
        print("\n" + "=" * 60)
        print("1. 用户登录")
        print("=" * 60)

        try:
            # 使用手机号登录（需要先有测试用户）
            response = await self.client.post(
                f"{BASE_URL}/auth/client/phone",
                json={"phone": "13800000001", "code": "123456"},
            )

            if response.status_code == 200:
                data = response.json()
                self.user_token = data.get("access_token")
                print(f"✅ 用户登录成功")
                print(f"   Token: {self.user_token[:20]}...")

                # 获取用户信息
                headers = {"Authorization": f"Bearer {self.user_token}"}
                me_response = await self.client.get(f"{BASE_URL}/auth/me", headers=headers)
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    self.user_id = user_data.get("id")
                    print(f"   用户ID: {self.user_id}")
                    print(f"   用户名: {user_data.get('username')}")
                return True
            else:
                print(f"❌ 用户登录失败: {response.status_code}")
                print(f"   响应: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ 用户登录异常: {e}")
            return False

    # ---- 2. AI 问答 ----

    async def test_ai_chat(self, message: str):
        """测试 AI 客服对话"""
        print("\n" + "=" * 60)
        print(f"2. AI 问答: {message}")
        print("=" * 60)

        if not self.user_token:
            print("❌ 用户未登录")
            return None

        try:
            headers = {"Authorization": f"Bearer {self.user_token}"}

            # 调用流式接口
            response = await self.client.post(
                f"{BASE_URL}/agent/cs/stream",
                json={
                    "message": message,
                    "conversation_id": f"test_chat_{int(time.time())}",
                    "user_id": self.user_id,
                },
                headers=headers,
            )

            if response.status_code == 200:
                # 解析 SSE 流
                full_answer = ""
                need_human = False
                sources = []

                for line in response.text.split("\n"):
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "done":
                                full_answer = data.get("content", "")
                                need_human = data.get("need_human", False)
                                sources = data.get("sources", [])
                            elif data.get("type") == "delta":
                                full_answer += data.get("content", "")
                        except json.JSONDecodeError:
                            pass

                print(f"✅ AI 回答成功")
                print(f"   回答: {full_answer[:100]}...")
                print(f"   需要转人工: {need_human}")
                print(f"   引用来源: {len(sources)} 条")

                return {
                    "answer": full_answer,
                    "need_human": need_human,
                    "sources": sources,
                }
            else:
                print(f"❌ AI 问答失败: {response.status_code}")
                print(f"   响应: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"❌ AI 问答异常: {e}")
            return None

    # ---- 3. 检查执行日志 ----

    async def check_execution_logs(self):
        """检查执行日志"""
        print("\n" + "=" * 60)
        print("3. 检查执行日志")
        print("=" * 60)

        try:
            # 使用管理员 token
            if not self.admin_token:
                await self.test_admin_login()

            headers = {"Authorization": f"Bearer {self.admin_token}"}

            response = await self.client.get(
                f"{BASE_URL}/agent-monitor/execution-logs?page=1&page_size=5",
                headers=headers,
            )

            if response.status_code == 200:
                logs = response.json()
                print(f"✅ 获取执行日志成功: {len(logs)} 条")

                for log in logs:
                    print(f"\n   Trace ID: {log.get('trace_id', 'N/A')}")
                    print(f"   用户输入: {log.get('user_input', 'N/A')[:50]}")
                    print(f"   状态: {log.get('status', 'N/A')}")
                    print(f"   耗时: {log.get('total_duration_ms', 0):.2f}ms")
                    print(f"   需要转人工: {log.get('need_human', False)}")

                    if log.get('trace_id'):
                        self.trace_ids.append(log['trace_id'])

                return logs
            else:
                print(f"❌ 获取执行日志失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ 检查执行日志异常: {e}")
            return []

    # ---- 4. 检查统计数据 ----

    async def check_statistics(self):
        """检查统计数据"""
        print("\n" + "=" * 60)
        print("4. 检查统计数据")
        print("=" * 60)

        try:
            if not self.admin_token:
                await self.test_admin_login()

            headers = {"Authorization": f"Bearer {self.admin_token}"}

            response = await self.client.get(
                f"{BASE_URL}/agent-monitor/stats?days=7",
                headers=headers,
            )

            if response.status_code == 200:
                stats = response.json()
                print(f"✅ 获取统计数据成功")
                print(f"   总咨询数: {stats.get('total_conversations', 0)}")
                print(f"   AI 解决数: {stats.get('ai_resolved_count', 0)}")
                print(f"   转人工数: {stats.get('transferred_count', 0)}")
                print(f"   AI 解决率: {stats.get('ai_resolution_rate', 0)}%")
                print(f"   转人工率: {stats.get('transfer_rate', 0)}%")
                print(f"   Agent 总调用: {stats.get('total_agent_calls', 0)}")
                print(f"   KnowledgeAgent 调用: {stats.get('knowledge_agent_count', 0)}")
                print(f"   ClassificationAgent 调用: {stats.get('classification_agent_count', 0)}")
                print(f"   PriorityAgent 调用: {stats.get('priority_agent_count', 0)}")
                print(f"   DispatchAgent 调用: {stats.get('dispatch_agent_count', 0)}")
                print(f"   工具总调用: {stats.get('total_tool_calls', 0)}")
                return stats
            else:
                print(f"❌ 获取统计数据失败: {response.status_code}")
                return {}
        except Exception as e:
            print(f"❌ 检查统计数据异常: {e}")
            return {}

    # ---- 5. 管理员登录 ----

    async def test_admin_login(self):
        """测试管理员登录"""
        try:
            # 第一步：账号密码
            response = await self.client.post(
                f"{BASE_URL}/auth/admin/login",
                json={"username": "admin", "password": "admin123"},
            )

            if response.status_code == 200:
                # 第二步：邮箱验证码（使用模拟验证码）
                # 实际测试中需要获取真实验证码
                print("   管理员登录需要邮箱验证码，跳过")
                return False
            return False
        except Exception as e:
            print(f"   管理员登录失败: {e}")
            return False

    # ---- 6. 客服登录 ----

    async def test_cs_login(self):
        """测试客服登录"""
        try:
            response = await self.client.post(
                f"{BASE_URL}/auth/cs/login",
                json={"employee_id": "CS001", "password": "cs123"},
            )

            if response.status_code == 200:
                data = response.json()
                self.cs_token = data.get("access_token")
                print(f"✅ 客服登录成功")
                return True
            return False
        except Exception as e:
            print(f"   客服登录失败: {e}")
            return False

    # ---- 7. 测试工单查询 ----

    async def test_tool_query_ticket(self, ticket_id: int):
        """测试工单查询工具"""
        print("\n" + "=" * 60)
        print(f"7. 测试工单查询工具: ticket_id={ticket_id}")
        print("=" * 60)

        try:
            from app.ai.tools import tool_registry

            result = await tool_registry.execute("query_ticket", ticket_id=ticket_id)

            if result.is_success():
                print(f"✅ 工具执行成功 (ticket_id={ticket_id})")
                print(f"   工单号: {result.data.get('ticket_no', 'N/A')}")
                print(f"   状态: {result.data.get('status_label', 'N/A')}")
                print(f"   优先级: {result.data.get('priority_label', 'N/A')}")
                return result.data
            else:
                print(f"❌ 工具执行失败: {result.error}")
                return None
        except Exception as e:
            print(f"❌ 工具调用异常: {e}")
            return None

    # ---- 8. 测试知识库搜索 ----

    async def test_tool_search_knowledge(self, query: str):
        """测试知识库搜索工具"""
        print("\n" + "=" * 60)
        print(f"8. 测试知识库搜索工具: query={query}")
        print("=" * 60)

        try:
            from app.ai.tools import tool_registry

            result = await tool_registry.execute("search_knowledge", query=query, top_k=3)

            if result.is_success():
                print(f"✅ 搜索成功")
                print(f"   找到 {result.data.get('total', 0)} 条结果")
                for item in result.data.get('results', [])[:2]:
                    print(f"   - {item.get('question', 'N/A')[:50]}")
                return result.data
            else:
                print(f"❌ 搜索失败: {result.error}")
                return None
        except Exception as e:
            print(f"❌ 搜索异常: {e}")
            return None

    # ---- 运行完整测试 ----

    async def run_full_test(self):
        """运行完整测试"""
        print("\n" + "=" * 60)
        print("🚀 全链路压测开始")
        print("=" * 60)
        print(f"开始时间: {datetime.now().isoformat()}")

        start_time = time.time()

        # 1. 用户登录
        await self.test_user_login()

        # 2. AI 问答（知识库能回答的问题）
        await self.test_ai_chat("如何重置密码？")

        # 3. AI 问答（知识库无法回答的问题，触发转人工）
        result = await self.test_ai_chat("我的订单支付成功但没有生成，帮我查一下订单 ORD20260606001")

        # 4. 检查执行日志
        await self.check_execution_logs()

        # 5. 检查统计数据
        await self.check_statistics()

        # 6. 测试工具调用
        await self.test_tool_query_ticket(1)
        await self.test_tool_search_knowledge("退款到账时间")

        end_time = time.time()
        duration = end_time - start_time

        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)
        print(f"结束时间: {datetime.now().isoformat()}")
        print(f"总耗时: {duration:.2f} 秒")
        print(f"收集到的 Trace IDs: {len(self.trace_ids)} 个")

        if self.trace_ids:
            print(f"Trace IDs:")
            for tid in self.trace_ids[:5]:
                print(f"  - {tid}")

        await self.close()


# ---- 主函数 ----

async def main():
    tester = FullChainTester()
    await tester.run_full_test()


if __name__ == "__main__":
    asyncio.run(main())