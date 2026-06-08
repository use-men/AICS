/**
 * DashboardPage — 用户端工作台（带真实数据 + 图表）
 */

import { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Typography, Empty, Spin } from 'antd';
import {
  FileTextOutlined, ClockCircleOutlined, CheckCircleOutlined,
  AlertOutlined, MessageOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { fetchTickets } from '@/shared/api/ticket';

const { Title, Text } = Typography;

const STATUS_COLORS: Record<string, string> = {
  pending: '#ff4d4f',
  assigned: '#faad14',
  processing: '#1890ff',
  resolved: '#52c41a',
  closed: '#8c8c8c',
};
const STATUS_LABELS: Record<string, string> = {
  pending: '待分配',
  assigned: '已分配',
  processing: '处理中',
  resolved: '已解决',
  closed: '已关闭',
};

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [tickets, setTickets] = useState<any[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        // 获取所有工单（取前 200 条用于统计）
        const res: any = await fetchTickets({ page: 1 });
        setTickets(res.data || []);
        setTotal(res.total || 0);
      } catch {}
      finally { setLoading(false); }
    };
    load();
  }, []);

  // 统计各状态数量
  const statusCount = tickets.reduce((acc: Record<string, number>, t: any) => {
    acc[t.status] = (acc[t.status] || 0) + 1;
    return acc;
  }, {});

  const pendingCount = (statusCount['pending'] || 0) + (statusCount['assigned'] || 0);
  const processingCount = statusCount['processing'] || 0;
  const resolvedCount = (statusCount['resolved'] || 0) + (statusCount['closed'] || 0);

  // 工单类型分布饼图
  const TYPE_MAP: Record<string, string> = { after_sales: '售后咨询', technical: '技术支持', refund: '退款申请', complaint: '投诉建议' };
  const typeCount = tickets.reduce((acc: Record<string, number>, t: any) => {
    const label = TYPE_MAP[t.ticket_type as string] || t.ticket_type;
    acc[label] = (acc[label] || 0) + 1;
    return acc;
  }, {});

  const pieOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    color: ['#667eea', '#764ba2', '#f093fb', '#4facfe'],
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%' },
      data: Object.entries(typeCount).map(([name, value]) => ({ name, value })),
    }],
  };

  // 优先级分布柱状图
  const PRIORITY_MAP: Record<string, string> = { urgent: '紧急', high: '高', medium: '中', low: '低' };
  const priorityCount = tickets.reduce((acc: Record<string, number>, t: any) => {
    const label = PRIORITY_MAP[t.priority as string] || t.priority;
    acc[label] = (acc[label] || 0) + 1;
    return acc;
  }, {});

  const barOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['紧急', '高', '中', '低'] },
    yAxis: { type: 'value', minInterval: 1 },
    grid: { left: 40, right: 20, bottom: 30, top: 10 },
    series: [{
      type: 'bar',
      barWidth: 32,
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: (params: any) => {
          const colors = ['#ff4d4f', '#faad14', '#1890ff', '#52c41a'];
          return colors[params.dataIndex] || '#667eea';
        },
      },
      data: ['紧急', '高', '中', '低'].map(p => priorityCount[p] || 0),
    }],
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>工作台</Title>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card hoverable onClick={() => navigate('/tickets')} style={{ borderRadius: 8 }}>
            <Statistic title="工单总数" value={total} prefix={<FileTextOutlined style={{ color: '#667eea' }} />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable style={{ borderRadius: 8 }}>
            <Statistic title="待处理" value={pendingCount} prefix={<ClockCircleOutlined style={{ color: '#faad14' }} />} valueStyle={{ color: '#faad14' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable style={{ borderRadius: 8 }}>
            <Statistic title="处理中" value={processingCount} prefix={<AlertOutlined style={{ color: '#1890ff' }} />} valueStyle={{ color: '#1890ff' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable style={{ borderRadius: 8 }}>
            <Statistic title="已解决" value={resolvedCount} prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
      </Row>

      {/* 图表 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title="工单类型分布" style={{ borderRadius: 8 }}>
            {Object.keys(typeCount).length > 0
              ? <ReactECharts option={pieOption} style={{ height: 280 }} />
              : <Empty description="暂无数据" />}
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="优先级分布" style={{ borderRadius: 8 }}>
            {tickets.length > 0
              ? <ReactECharts option={barOption} style={{ height: 280 }} />
              : <Empty description="暂无数据" />}
          </Card>
        </Col>
      </Row>

      {/* 最近工单 */}
      {tickets.length > 0 && (
        <Card title="最近工单" style={{ borderRadius: 8, marginTop: 16 }}>
          {tickets.slice(0, 5).map((t: any) => (
            <div key={t.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #f0f0f0', cursor: 'pointer' }}
              onClick={() => navigate(`/tickets/${t.id}`)}>
              <div>
                <Text strong style={{ fontFamily: 'monospace', marginRight: 12 }}>{t.ticket_no}</Text>
                <Text>{t.title}</Text>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 12, background: `${STATUS_COLORS[t.status]}15`, color: STATUS_COLORS[t.status] }}>
                  {STATUS_LABELS[t.status] || t.status}
                </span>
                <Text type="secondary" style={{ fontSize: 12 }}>{t.created_at ? new Date(t.created_at).toLocaleString('zh-CN') : ''}</Text>
              </div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
};

export default DashboardPage;
