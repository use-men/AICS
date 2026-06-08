/**
 * TraceDetailPage — Agent 执行链路详情页
 *
 * 展示：
 * - 用户问题
 * - AI回答
 * - Agent执行链（Timeline）
 * - Tool调用详情（Table）
 * - 耗时统计
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Typography, Tag, Space, Timeline, Table, Descriptions,
  Spin, Button, Row, Col, Statistic, Divider, Empty,
} from 'antd';
import {
  ArrowLeftOutlined, ClockCircleOutlined, CheckCircleOutlined,
  CloseCircleOutlined, LoadingOutlined, RobotOutlined, ToolOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { Title, Text, Paragraph } = Typography;

// ---- 类型定义 ----

interface AgentLog {
  agent_name: string;
  agent_type: string | null;
  start_time: string | null;
  end_time: string | null;
  duration_ms: number;
  status: string;
  input_summary: string;
  output_summary: string;
  error: string | null;
}

interface ToolLog {
  id: number;
  trace_id: string;
  tool_name: string;
  tool_input: Record<string, any> | null;
  tool_output: string | null;
  status: string;
  error: string | null;
  duration_ms: number;
  created_at: string | null;
}

interface TraceDetail {
  id: number;
  trace_id: string;
  user_id: number;
  user_input: string;
  answer: string | null;
  need_human: boolean;
  ticket_type: string | null;
  ticket_priority: string | null;
  ticket_id: number | null;
  assignee_id: number | null;
  status: string;
  total_duration_ms: number;
  agent_count: number;
  tool_count: number;
  agent_logs: AgentLog[];
  tool_logs: ToolLog[];
  created_at: string | null;
}

// ---- Agent 名称映射 ----

const AGENT_NAMES: Record<string, string> = {
  'knowledge_agent': 'KnowledgeAgent',
  'ticket_classifier': 'ClassificationAgent',
  'priority_analyzer': 'PriorityAgent',
  'ticket_creator': 'TicketCreatorAgent',
  'dispatcher': 'DispatchAgent',
  'tool_calling': 'ToolCallingAgent',
  'supervisor': 'SupervisorAgent',
};

const AGENT_COLORS: Record<string, string> = {
  'knowledge_agent': '#1890ff',
  'ticket_classifier': '#52c41a',
  'priority_analyzer': '#faad14',
  'ticket_creator': '#722ed1',
  'dispatcher': '#13c2c2',
  'tool_calling': '#eb2f96',
  'supervisor': '#f5222d',
};

// ---- 主组件 ----

const TraceDetailPage: React.FC = () => {
  const { traceId } = useParams<{ traceId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [trace, setTrace] = useState<TraceDetail | null>(null);

  // 获取详情
  useEffect(() => {
    fetchTraceDetail();
  }, [traceId]);

  const fetchTraceDetail = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`/api/v1/agent-monitor/execution-logs/${traceId}`, { headers });
      if (res.ok) {
        const data = await res.json();
        setTrace(data);
      }
    } catch (error) {
      console.error('获取详情失败:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Spin size="large" style={{ display: 'block', marginTop: 100, textAlign: 'center' }} />;
  }

  if (!trace) {
    return <Empty description="执行日志不存在" />;
  }

  // Agent 执行链 Timeline 数据
  const agentTimeline = trace.agent_logs.map((log, index) => ({
    color: log.status === 'completed' ? 'green' : log.status === 'failed' ? 'red' : 'blue',
    dot: log.status === 'completed'
      ? <CheckCircleOutlined style={{ color: '#52c41a' }} />
      : log.status === 'failed'
      ? <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
      : <LoadingOutlined style={{ color: '#1890ff' }} />,
    children: (
      <div>
        <Space>
          <Tag color={AGENT_COLORS[log.agent_name] || '#666'}>
            {AGENT_NAMES[log.agent_name] || log.agent_name}
          </Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {log.duration_ms.toFixed(0)}ms
          </Text>
          <Tag color={log.status === 'completed' ? 'success' : 'error'}>
            {log.status === 'completed' ? '成功' : '失败'}
          </Tag>
        </Space>
        {log.error && (
          <div style={{ marginTop: 4 }}>
            <Text type="danger" style={{ fontSize: 12 }}>错误: {log.error}</Text>
          </div>
        )}
      </div>
    ),
  }));

  // Tool 调用详情 Table 数据
  const toolColumns = [
    {
      title: '工具名称',
      dataIndex: 'tool_name',
      key: 'tool_name',
      render: (name: string) => <Tag color="blue">{name}</Tag>,
    },
    {
      title: '输入参数',
      dataIndex: 'tool_input',
      key: 'tool_input',
      render: (input: Record<string, any>) => (
        <pre style={{ margin: 0, fontSize: 12, background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
          {JSON.stringify(input, null, 2)}
        </pre>
      ),
    },
    {
      title: '输出结果',
      dataIndex: 'tool_output',
      key: 'tool_output',
      render: (output: string) => (
        <pre style={{ margin: 0, fontSize: 12, background: '#f5f5f5', padding: 8, borderRadius: 4, maxHeight: 150, overflow: 'auto' }}>
          {output || '无'}
        </pre>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'completed' ? 'success' : 'error'}>
          {status === 'completed' ? '成功' : '失败'}
        </Tag>
      ),
    },
    {
      title: '耗时',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      render: (ms: number) => `${ms.toFixed(0)}ms`,
    },
  ];

  return (
    <div style={{ padding: 0 }}>
      {/* 头部 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} />
        <Title level={4} style={{ margin: 0 }}>Trace 详情</Title>
        <Tag>{trace.trace_id.slice(0, 8)}...</Tag>
      </div>

      {/* 基本信息 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总耗时"
              value={trace.total_duration_ms.toFixed(0)}
              suffix="ms"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Agent 调用"
              value={trace.agent_count}
              prefix={<RobotOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="工具调用"
              value={trace.tool_count}
              prefix={<ToolOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="状态"
              value={trace.status === 'completed' ? '成功' : '失败'}
              valueStyle={{ color: trace.status === 'completed' ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 用户问题和 AI 回答 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="用户问题" size="small">
            <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {trace.user_input}
            </Paragraph>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="AI 回答" size="small">
            <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {trace.answer || '无回答'}
            </Paragraph>
          </Card>
        </Col>
      </Row>

      {/* Agent 执行链 */}
      <Card
        title={<span><RobotOutlined /> Agent 执行链</span>}
        size="small"
        style={{ marginBottom: 16 }}
      >
        {trace.agent_logs.length > 0 ? (
          <Timeline items={agentTimeline} />
        ) : (
          <Empty description="无 Agent 执行记录" />
        )}
      </Card>

      {/* Tool 调用详情 */}
      <Card
        title={<span><ToolOutlined /> Tool 调用详情</span>}
        size="small"
        style={{ marginBottom: 16 }}
      >
        {trace.tool_logs.length > 0 ? (
          <Table
            dataSource={trace.tool_logs}
            columns={toolColumns}
            rowKey="id"
            pagination={false}
            size="small"
          />
        ) : (
          <Empty description="无工具调用记录" />
        )}
      </Card>

      {/* 基本信息 */}
      <Card title="基本信息" size="small">
        <Descriptions column={2} size="small">
          <Descriptions.Item label="Trace ID">
            <Text copyable>{trace.trace_id}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="用户 ID">{trace.user_id}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {trace.created_at ? dayjs(trace.created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="需要转人工">
            <Tag color={trace.need_human ? 'orange' : 'green'}>
              {trace.need_human ? '是' : '否'}
            </Tag>
          </Descriptions.Item>
          {trace.ticket_type && (
            <Descriptions.Item label="工单类型">{trace.ticket_type}</Descriptions.Item>
          )}
          {trace.ticket_priority && (
            <Descriptions.Item label="工单优先级">{trace.ticket_priority}</Descriptions.Item>
          )}
          {trace.ticket_id && (
            <Descriptions.Item label="工单 ID">{trace.ticket_id}</Descriptions.Item>
          )}
          {trace.assignee_id && (
            <Descriptions.Item label="分配客服 ID">{trace.assignee_id}</Descriptions.Item>
          )}
        </Descriptions>
      </Card>
    </div>
  );
};

export default TraceDetailPage;
