/**
 * AgentMonitorPage — 管理端 Agent 监控中心
 *
 * 展示: Agent调用次数、AI解决率、自动派单率、转人工率、ECharts图表
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Row, Col, Typography, Statistic, Table, Tag, Space, Progress, Divider, Spin, Button, Select } from 'antd';
import {
  RobotOutlined, CheckCircleOutlined, SwapOutlined,
  TeamOutlined, BarChartOutlined, ThunderboltOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

// ---- API 接口 ----

interface AgentStats {
  knowledge_agent_count: number;
  classification_agent_count: number;
  priority_agent_count: number;
  ticket_creator_agent_count: number;
  dispatch_agent_count: number;
  tool_calling_agent_count: number;
  total_agent_calls: number;
  successful_agent_calls: number;
  failed_agent_calls: number;
  avg_agent_duration_ms: number;
  query_ticket_count: number;
  query_order_count: number;
  query_refund_count: number;
  search_knowledge_count: number;
  search_web_count: number;
  total_tool_calls: number;
  successful_tool_calls: number;
  failed_tool_calls: number;
  avg_tool_duration_ms: number;
  total_conversations: number;
  ai_resolved_count: number;
  transferred_count: number;
  ai_resolution_rate: number;
  transfer_rate: number;
  auto_dispatch_rate: number;
}

interface ExecutionLog {
  id: number;
  trace_id: string;
  user_id: number;
  user_input: string;
  answer: string | null;
  need_human: boolean;
  ticket_type: string | null;
  ticket_priority: string | null;
  status: string;
  total_duration_ms: number;
  agent_count: number;
  tool_count: number;
  agent_logs: any;
  tool_logs: any;
  created_at: string | null;
}

interface DailyStats {
  date: string;
  stats: AgentStats;
}

// ---- 统计卡片组件 ----

const StatCard: React.FC<{
  title: string;
  value: number | string;
  suffix?: string;
  icon: React.ReactNode;
  color: string;
  percent?: number;
}> = ({ title, value, suffix, icon, color, percent }) => (
  <Card>
    <Space direction="vertical" style={{ width: '100%' }}>
      <Space>
        <div style={{ ...styles.iconBox, background: `${color}15` }}>
          {icon}
        </div>
        <Text type="secondary">{title}</Text>
      </Space>
      <Statistic
        value={value}
        suffix={suffix}
        valueStyle={{ color, fontSize: 28, fontWeight: 600 }}
      />
      {percent !== undefined && (
        <Progress
          percent={Math.round(percent * 100)}
          strokeColor={color}
          size="small"
          showInfo={false}
        />
      )}
    </Space>
  </Card>
);

// ---- 主组件 ----

const AgentMonitorPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<AgentStats | null>(null);
  const [dailyStats, setDailyStats] = useState<DailyStats[]>([]);
  const [executionLogs, setExecutionLogs] = useState<ExecutionLog[]>([]);
  const [days, setDays] = useState(7);

  // 获取统计数据
  const fetchStats = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // 获取统计数据
      const statsRes = await fetch(`/api/v1/agent-monitor/stats?days=${days}`, { headers });
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      // 获取每日统计
      const dailyRes = await fetch(`/api/v1/agent-monitor/daily-stats?days=${days}`, { headers });
      if (dailyRes.ok) {
        const dailyData = await dailyRes.json();
        setDailyStats(dailyData);
      }

      // 获取执行日志
      const logsRes = await fetch(`/api/v1/agent-monitor/execution-logs?page=1&page_size=10`, { headers });
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setExecutionLogs(logsData);
      }
    } catch (error) {
      console.error('获取数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [days]);

  // Agent 调用数据
  const agentCallsData = stats ? [
    { agent: 'KnowledgeAgent', calls: stats.knowledge_agent_count, avgTime: stats.avg_agent_duration_ms, successRate: stats.total_agent_calls > 0 ? stats.successful_agent_calls / stats.total_agent_calls : 0 },
    { agent: 'ClassificationAgent', calls: stats.classification_agent_count, avgTime: stats.avg_agent_duration_ms, successRate: stats.total_agent_calls > 0 ? stats.successful_agent_calls / stats.total_agent_calls : 0 },
    { agent: 'PriorityAgent', calls: stats.priority_agent_count, avgTime: stats.avg_agent_duration_ms, successRate: stats.total_agent_calls > 0 ? stats.successful_agent_calls / stats.total_agent_calls : 0 },
    { agent: 'TicketCreatorAgent', calls: stats.ticket_creator_agent_count, avgTime: stats.avg_agent_duration_ms, successRate: stats.total_agent_calls > 0 ? stats.successful_agent_calls / stats.total_agent_calls : 0 },
    { agent: 'DispatchAgent', calls: stats.dispatch_agent_count, avgTime: stats.avg_agent_duration_ms, successRate: stats.total_agent_calls > 0 ? stats.successful_agent_calls / stats.total_agent_calls : 0 },
    { agent: 'ToolCallingAgent', calls: stats.tool_calling_agent_count, avgTime: stats.avg_agent_duration_ms, successRate: stats.total_agent_calls > 0 ? stats.successful_agent_calls / stats.total_agent_calls : 0 },
  ] : [];

  // ECharts 配置 - Agent 调用趋势
  const agentTrendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['AI解决', '转人工'] },
    xAxis: { type: 'category', data: dailyStats.map(d => d.date) },
    yAxis: { type: 'value' },
    series: [
      {
        name: 'AI解决',
        type: 'line',
        smooth: true,
        data: dailyStats.map(d => d.stats.ai_resolved_count),
        itemStyle: { color: '#52c41a' },
      },
      {
        name: '转人工',
        type: 'line',
        smooth: true,
        data: dailyStats.map(d => d.stats.transferred_count),
        itemStyle: { color: '#fa8c16' },
      },
    ],
  };

  // ECharts 配置 - Agent 调用分布
  const agentPieOption = stats ? {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [
      {
        type: 'pie',
        radius: '50%',
        data: [
          { value: stats.knowledge_agent_count, name: 'KnowledgeAgent' },
          { value: stats.classification_agent_count, name: 'ClassificationAgent' },
          { value: stats.priority_agent_count, name: 'PriorityAgent' },
          { value: stats.ticket_creator_agent_count, name: 'TicketCreatorAgent' },
          { value: stats.dispatch_agent_count, name: 'DispatchAgent' },
          { value: stats.tool_calling_agent_count, name: 'ToolCallingAgent' },
        ],
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' },
        },
      },
    ],
  } : {};

  // ECharts 配置 - 工具调用分布
  const toolPieOption = stats ? {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [
      {
        type: 'pie',
        radius: '50%',
        data: [
          { value: stats.query_ticket_count, name: 'query_ticket' },
          { value: stats.query_order_count, name: 'query_order' },
          { value: stats.query_refund_count, name: 'query_refund' },
          { value: stats.search_knowledge_count, name: 'search_knowledge' },
          { value: stats.search_web_count, name: 'search_web' },
        ],
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' },
        },
      },
    ],
  } : {};

  // Agent 调用列表 columns
  const agentColumns = [
    {
      title: 'Agent 名称',
      dataIndex: 'agent',
      key: 'agent',
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: '调用次数',
      dataIndex: 'calls',
      key: 'calls',
      render: (v: number) => <Statistic value={v} valueStyle={{ fontSize: 14 }} />,
    },
    {
      title: '平均耗时',
      dataIndex: 'avgTime',
      key: 'avgTime',
      render: (v: number) => <Tag color="blue">{v.toFixed(1)}ms</Tag>,
    },
    {
      title: '成功率',
      dataIndex: 'successRate',
      key: 'successRate',
      render: (v: number) => (
        <Progress
          percent={Math.round(v * 100)}
          size="small"
          strokeColor={v >= 0.95 ? '#52c41a' : v >= 0.9 ? '#faad14' : '#f5222d'}
        />
      ),
    },
  ];

  // 执行日志 columns
  const logColumns = [
    {
      title: 'Trace ID',
      dataIndex: 'trace_id',
      key: 'trace_id',
      width: 200,
      ellipsis: true,
      render: (v: string) => (
        <a
          onClick={() => navigate(`/admin/agent-monitor/${v}`)}
          style={{ cursor: 'pointer', color: '#1890ff' }}
        >
          {v.slice(0, 8)}...
        </a>
      ),
    },
    {
      title: '用户问题',
      dataIndex: 'user_input',
      key: 'user_input',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => (
        <Tag color={v === 'completed' ? 'success' : v === 'failed' ? 'error' : 'processing'}>
          {v === 'completed' ? '成功' : v === 'failed' ? '失败' : '处理中'}
        </Tag>
      ),
    },
    {
      title: '耗时',
      dataIndex: 'total_duration_ms',
      key: 'total_duration_ms',
      render: (v: number) => <Tag color="blue">{v.toFixed(0)}ms</Tag>,
    },
    {
      title: 'Agent数',
      dataIndex: 'agent_count',
      key: 'agent_count',
      render: (v: number) => <Tag>{v}</Tag>,
    },
    {
      title: '工具数',
      dataIndex: 'tool_count',
      key: 'tool_count',
      render: (v: number) => <Tag>{v}</Tag>,
    },
    {
      title: '需要转人工',
      dataIndex: 'need_human',
      key: 'need_human',
      render: (v: boolean) => (
        <Tag color={v ? 'orange' : 'green'}>{v ? '是' : '否'}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => v ? dayjs(v).format('MM-DD HH:mm:ss') : '-',
    },
  ];

  return (
    <Spin spinning={loading}>
      <div style={{ padding: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <Title level={4} style={{ margin: 0 }}>
            <RobotOutlined /> Agent 监控中心
          </Title>
          <Space>
            <Select value={days} onChange={setDays} style={{ width: 120 }}>
              <Select.Option value={7}>最近 7 天</Select.Option>
              <Select.Option value={14}>最近 14 天</Select.Option>
              <Select.Option value={30}>最近 30 天</Select.Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={fetchStats}>刷新</Button>
          </Space>
        </div>

        {/* 统计卡片 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="Agent 总调用"
              value={stats?.total_agent_calls || 0}
              icon={<BarChartOutlined style={{ fontSize: 20, color: '#667eea' }} />}
              color="#667eea"
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="AI 解决率"
              value={`${stats?.ai_resolution_rate || 0}%`}
              icon={<CheckCircleOutlined style={{ fontSize: 20, color: '#52c41a' }} />}
              color="#52c41a"
              percent={(stats?.ai_resolution_rate || 0) / 100}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="自动派单率"
              value={`${stats?.auto_dispatch_rate || 0}%`}
              icon={<SwapOutlined style={{ fontSize: 20, color: '#1890ff' }} />}
              color="#1890ff"
              percent={(stats?.auto_dispatch_rate || 0) / 100}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <StatCard
              title="转人工率"
              value={`${stats?.transfer_rate || 0}%`}
              icon={<TeamOutlined style={{ fontSize: 20, color: '#fa8c16' }} />}
              color="#fa8c16"
              percent={(stats?.transfer_rate || 0) / 100}
            />
          </Col>
        </Row>

        <Divider />

        {/* ECharts 图表 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="AI 解决 vs 转人工 趋势">
              <ReactECharts option={agentTrendOption} style={{ height: 300 }} />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="Agent 调用分布">
              <ReactECharts option={agentPieOption} style={{ height: 300 }} />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="工具调用分布">
              <ReactECharts option={toolPieOption} style={{ height: 300 }} />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="Agent 调用详情">
              <Table
                dataSource={agentCallsData}
                columns={agentColumns}
                rowKey="agent"
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
        </Row>

        <Divider />

        {/* 执行日志 */}
        <Card title={<><ThunderboltOutlined /> 最近执行日志</>}>
          <Table
            dataSource={executionLogs}
            columns={logColumns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
            size="small"
          />
        </Card>
      </div>
    </Spin>
  );
};

// ---- 样式 ----

const styles: Record<string, React.CSSProperties> = {
  iconBox: {
    width: 40,
    height: 40,
    borderRadius: 10,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
};

export default AgentMonitorPage;
