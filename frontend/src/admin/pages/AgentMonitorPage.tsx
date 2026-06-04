/**
 * AgentMonitorPage — 管理端 Agent 监控中心
 *
 * 展示: Agent调用次数、AI解决率、自动派单率、转人工率
 */

import { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, Statistic, Table, Tag, Space, Progress, Divider } from 'antd';
import {
  RobotOutlined, CheckCircleOutlined, SwapOutlined,
  TeamOutlined, BarChartOutlined, ThunderboltOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

// ---- 模拟数据（实际应从 API 获取） ----

const MOCK_STATS = {
  totalCalls: 1256,
  aiResolved: 892,
  aiResolveRate: 0.71,
  autoDispatched: 634,
  autoDispatchRate: 0.85,
  transferToHuman: 364,
  transferRate: 0.29,
  avgResponseTime: 1.2,
};

const MOCK_AGENT_CALLS = [
  { agent: 'TicketClassificationAgent', calls: 1256, avgTime: 0.8, successRate: 0.98 },
  { agent: 'PriorityAnalyzerAgent', calls: 1256, avgTime: 0.6, successRate: 0.99 },
  { agent: 'KnowledgeAgent', calls: 1089, avgTime: 1.5, successRate: 0.95 },
  { agent: 'DispatchAgent', calls: 634, avgTime: 0.3, successRate: 1.0 },
  { agent: 'CustomerServiceAgent', calls: 1089, avgTime: 2.1, successRate: 0.93 },
  { agent: 'TicketCreationAgent', calls: 364, avgTime: 1.8, successRate: 0.97 },
];

const MOCK_RECENT_CONVERSATIONS = [
  { id: 1, time: '22:30:15', question: '怎么登录系统？', answer: 'AI直接回答', type: 'after_sales', resolved: true },
  { id: 2, time: '22:28:42', question: '产品有质量问题', answer: '转人工', type: 'refund', resolved: false },
  { id: 3, time: '22:25:18', question: '系统崩溃了', answer: 'AI直接回答', type: 'technical', resolved: true },
  { id: 4, time: '22:22:05', question: '如何配置通知？', answer: 'AI直接回答', type: 'after_sales', resolved: true },
  { id: 5, time: '22:18:33', question: '申请退款', answer: '转人工', type: 'refund', resolved: false },
];

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
  const [stats, setStats] = useState(MOCK_STATS);
  const [agentCalls, setAgentCalls] = useState(MOCK_AGENT_CALLS);
  const [conversations, setConversations] = useState(MOCK_RECENT_CONVERSATIONS);

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
      render: (v: number) => <Tag color="blue">{v}s</Tag>,
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

  // 最近对话列表 columns
  const conversationColumns = [
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      width: 80,
    },
    {
      title: '用户问题',
      dataIndex: 'question',
      key: 'question',
      ellipsis: true,
    },
    {
      title: '处理方式',
      dataIndex: 'answer',
      key: 'answer',
      render: (v: string) => (
        <Tag color={v === 'AI直接回答' ? 'green' : 'orange'}>{v}</Tag>
      ),
    },
    {
      title: '分类',
      dataIndex: 'type',
      key: 'type',
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'resolved',
      key: 'resolved',
      render: (v: boolean) => (
        <Tag color={v ? 'success' : 'processing'}>{v ? '已解决' : '处理中'}</Tag>
      ),
    },
  ];

  return (
    <div style={{ padding: 0 }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        <RobotOutlined /> Agent 监控中心
      </Title>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="Agent 总调用"
            value={stats.totalCalls}
            icon={<BarChartOutlined style={{ fontSize: 20, color: '#667eea' }} />}
            color="#667eea"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="AI 解决率"
            value={`${Math.round(stats.aiResolveRate * 100)}%`}
            icon={<CheckCircleOutlined style={{ fontSize: 20, color: '#52c41a' }} />}
            color="#52c41a"
            percent={stats.aiResolveRate}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="自动派单率"
            value={`${Math.round(stats.autoDispatchRate * 100)}%`}
            icon={<SwapOutlined style={{ fontSize: 20, color: '#1890ff' }} />}
            color="#1890ff"
            percent={stats.autoDispatchRate}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="转人工率"
            value={`${Math.round(stats.transferRate * 100)}%`}
            icon={<TeamOutlined style={{ fontSize: 20, color: '#fa8c16' }} />}
            color="#fa8c16"
            percent={stats.transferRate}
          />
        </Col>
      </Row>

      <Divider />

      {/* Agent 调用详情 */}
      <Row gutter={16}>
        <Col xs={24} lg={14}>
          <Card title={<><ThunderboltOutlined /> Agent 调用详情</>}>
            <Table
              dataSource={agentCalls}
              columns={agentColumns}
              rowKey="agent"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title={<><BarChartOutlined /> 最近对话</>}>
            <Table
              dataSource={conversations}
              columns={conversationColumns}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
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
