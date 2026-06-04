/**
 * AdminDashboardPage — 管理端 AI 运营大屏
 *
 * 统计:
 * - 工单总数 / AI解决率 / 自动派单率 / 转人工率
 * - 平均响应时间 / 平均解决时长
 * - 工单趋势(折线图) / 类型分布(饼图) / 状态分布(环形图) / 优先级(柱状图)
 * - 客服排行(横向柱状图)
 */

import { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, Statistic, Spin, Table, Tag } from 'antd';
import {
  TagsOutlined, RobotOutlined, ThunderboltOutlined, SwapOutlined,
  ClockCircleOutlined, CheckCircleOutlined, RiseOutlined, TeamOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { getDashboardStats } from '@/shared/api/ticket';

const { Title, Text } = Typography;

const TYPE_LABELS: Record<string, string> = {
  after_sales: '售后咨询', technical: '技术支持', refund: '退款申请', complaint: '投诉建议',
};
const PRIORITY_COLORS: Record<string, string> = {
  urgent: 'red', high: 'orange', medium: 'blue', low: 'green',
};
const STATUS_COLORS: Record<string, string> = {
  pending: '#f5222d', assigned: '#faad14', processing: '#1890ff', resolved: '#52c41a', closed: '#d9d9d9',
};
const STATUS_LABELS: Record<string, string> = {
  pending: '待分配', assigned: '已分配', processing: '处理中', resolved: '已解决', closed: '已关闭',
};

const AdminDashboardPage: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" style={{ display: 'block', marginTop: 100, textAlign: 'center' }} />;
  if (!stats) return <div>加载失败</div>;

  // ---- 图表配置 ----

  /** 工单趋势折线图 */
  const trendOption = {
    tooltip: { trigger: 'axis' as const },
    grid: { top: 10, right: 20, bottom: 30, left: 50 },
    xAxis: { type: 'category' as const, data: stats.trend?.dates || [], boundaryGap: false },
    yAxis: { type: 'value' as const, minInterval: 1 },
    series: [{
      name: '工单数',
      type: 'line',
      data: stats.trend?.counts || [],
      smooth: true,
      areaStyle: { color: 'rgba(102,126,234,0.15)' },
      lineStyle: { color: '#667eea', width: 2 },
      itemStyle: { color: '#667eea' },
    }],
  };

  /** 工单类型饼图 */
  const typeOption = {
    tooltip: { trigger: 'item' as const, formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '45%'],
      data: Object.entries(stats.by_type || {}).map(([k, v]) => ({
        name: TYPE_LABELS[k] || k,
        value: v,
      })),
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' } },
    }],
  };

  /** 工单状态环形图 */
  const statusOption = {
    tooltip: { trigger: 'item' as const, formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' as const } },
      data: Object.entries(stats.by_status || {}).map(([k, v]) => ({
        name: STATUS_LABELS[k] || k,
        value: v,
        itemStyle: { color: STATUS_COLORS[k] },
      })),
    }],
  };

  /** 优先级柱状图 */
  const priorityOrder = ['urgent', 'high', 'medium', 'low'];
  const priorityLabels = ['紧急', '高', '中', '低'];
  const priorityOption = {
    tooltip: { trigger: 'axis' as const },
    grid: { top: 10, right: 20, bottom: 30, left: 50 },
    xAxis: {
      type: 'category' as const,
      data: priorityLabels,
    },
    yAxis: { type: 'value' as const, minInterval: 1 },
    series: [{
      type: 'bar',
      data: priorityOrder.map((k) => ({
        value: stats.by_priority?.[k] || 0,
        itemStyle: { color: PRIORITY_COLORS[k] },
      })),
      barWidth: '40%',
    }],
  };

  /** 客服排行横向柱状图 */
  const agentNames = (stats.agent_ranking || []).map((a: any) => a.name).reverse();
  const agentResolved = (stats.agent_ranking || []).map((a: any) => a.resolved).reverse();
  const agentOption = {
    tooltip: { trigger: 'axis' as const, axisPointer: { type: 'shadow' as const } },
    grid: { top: 10, right: 40, bottom: 10, left: 80 },
    xAxis: { type: 'value' as const, minInterval: 1 },
    yAxis: { type: 'category' as const, data: agentNames },
    series: [{
      type: 'bar',
      data: agentResolved,
      barWidth: '50%',
      label: { show: true, position: 'right' as const, fontSize: 12 },
      itemStyle: {
        color: {
          type: 'linear' as const,
          x: 0, y: 0, x2: 1, y2: 0,
          colorStops: [
            { offset: 0, color: '#667eea' },
            { offset: 1, color: '#764ba2' },
          ],
        },
        borderRadius: [0, 4, 4, 0],
      },
    }],
  };

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>AI 运营大屏</Title>

      {/* ---- 数字卡片 ---- */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={4}>
          <Card><Statistic title="工单总数" value={stats.total} prefix={<TagsOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card><Statistic title="AI 解决率" value={stats.ai_resolve_rate * 100} suffix="%" prefix={<RobotOutlined />} valueStyle={{ color: '#722ed1' }} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card><Statistic title="自动派单率" value={stats.auto_dispatch_rate * 100} suffix="%" prefix={<ThunderboltOutlined />} valueStyle={{ color: '#1890ff' }} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card><Statistic title="转人工率" value={stats.transfer_rate * 100} suffix="%" prefix={<SwapOutlined />} valueStyle={{ color: '#faad14' }} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card><Statistic title="平均响应" value={stats.avg_first_response_minutes} suffix="分钟" prefix={<ClockCircleOutlined />} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card><Statistic title="平均解决" value={stats.avg_resolve_minutes} suffix="分钟" prefix={<CheckCircleOutlined />} /></Card>
        </Col>
      </Row>

      {/* ---- 图表区域 ---- */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title={<span><RiseOutlined /> 工单趋势（近7天）</span>}>
            <ReactECharts option={trendOption} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="工单类型分布">
            <ReactECharts option={typeOption} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={8}>
          <Card title="工单状态">
            <ReactECharts option={statusOption} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="优先级分布">
            <ReactECharts option={priorityOption} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={<span><TeamOutlined /> 客服排行</span>}>
            {(stats.agent_ranking?.length || 0) > 0 ? (
              <ReactECharts option={agentOption} style={{ height: 280 }} />
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AdminDashboardPage;
