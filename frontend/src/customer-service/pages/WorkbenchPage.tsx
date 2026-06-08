/**
 * WorkbenchPage — 客服工作台（实时刷新）
 *
 * 功能:
 * - WebSocket 实时接收新工单
 * - 工单统计实时更新
 * - 一键接单/解决
 * - 新工单提示音
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, Row, Col, Typography, Statistic, Table, Tag, Button, Badge, Space, message, notification } from 'antd';
import {
  ClockCircleOutlined, ThunderboltOutlined, CheckCircleOutlined,
  UserOutlined, SoundOutlined, MutedOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAppSelector } from '@/store/hooks';
import { fetchTickets, acceptTicket, updateTicketStatus } from '@/shared/api/ticket';

const { Title, Text } = Typography;

const PRIORITY_COLORS: Record<string, string> = { urgent: 'red', high: 'orange', medium: 'blue', low: 'green' };
const PRIORITY_LABELS: Record<string, string> = { urgent: '紧急', high: '高', medium: '中', low: '低' };
const TYPE_LABELS: Record<string, string> = { after_sales: '售后咨询', technical: '技术支持', refund: '退款申请', complaint: '投诉建议' };
const STATUS_LABELS: Record<string, string> = { pending: '待分配', assigned: '已分配', processing: '处理中', resolved: '已解决', closed: '已关闭' };
const STATUS_COLORS: Record<string, string> = { pending: 'error', assigned: 'warning', processing: 'processing', resolved: 'success', closed: 'default' };

const WorkbenchPage: React.FC = () => {
  const navigate = useNavigate();
  const user = useAppSelector((s) => s.auth.user);
  const wsRef = useRef<WebSocket | null>(null);
  const [tickets, setTickets] = useState<any[]>([]);
  const [stats, setStats] = useState({ pending: 0, processing: 0, resolved: 0 });
  const [newTicketCount, setNewTicketCount] = useState(0);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [connected, setConnected] = useState(false);

  // ---- 获取工单列表 ----

  const fetchTicketData = useCallback(async () => {
    try {
      const res = await fetchTickets({ page: 1 });
      const data = res.data || [];
      setTickets(data);

      // 计算统计
      const pending = data.filter((t: any) => t.status === 'pending').length;
      const processing = data.filter((t: any) => t.status === 'processing').length;
      const resolved = data.filter((t: any) => t.status === 'resolved').length;
      setStats({ pending, processing, resolved });
    } catch {}
  }, []);

  useEffect(() => { fetchTicketData(); }, [fetchTicketData]);

  // ---- WebSocket 连接 ----

  useEffect(() => {
    if (!user?.id) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/service/${user.id}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log('[WS] 客服工作台已连接');
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === 'new_ticket') {
        // 新工单通知
        setNewTicketCount((prev) => prev + 1);
        fetchTicketData();

        // 浏览器通知
        notification.info({
          message: '新工单',
          description: msg.data?.title || '有新的工单需要处理',
          duration: 5,
        });

        // 提示音
        if (soundEnabled) {
          try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVggoKIeGBNVEpLZ3+Jk31kRj1TXG+LlYBfPjlaeZCOhGNHRlBfd5OUhGRNSk9Za3uXmIVlS0JJVWZ6l5eEZUk+Rk9hd5WUg2NGO0RMYHaUlINiRDZASGF0kZOCYEEzP0Nfb3yUkoBePy03QVVpeZSTgF08KDI+T2Z1kZB+cDczN0pWaXaRj4FqMy0yRVltd5CNgGgwKzBEW3F7kYyCaC4nLERfdX2RioBnLSUqQ2N6gZCJf2UpISZCaX6Dj4d8YCMcI0Bwg4iMg3VaHBgXQHKGjI2Gd1MVDBJAeIyQkop0UQYAD0N+kJeVkG9GA/4WRYaXm5uXd0MlBRhLh5qcnpqNNjUvGyBLiJ2goZyTMTAwHiVNj6Ckp52NOTMxIShQk6WnqJuMODIwJitVmKutqp80LS0sL1idrbCxnTgqKSswXqO0t7WaMiUmKjNkqbW5t5QnICYuOmu1vr2fiy8hIy8+c77Gx5+JLB8eKjpzxs3PloIpGBQjN3bN0tSbeR8UFSM8e9TX2ZNtEgwPGzx+2d3flF8LBwUaQYXe4OKVUgEAAQ==');
            audio.play();
          } catch {}
        }
      }

      if (msg.type === 'ticket_update') {
        // 工单状态更新
        fetchTicketData();
      }

      if (msg.type === 'dispatch_result') {
        // 派单结果
        fetchTicketData();
      }
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('[WS] 连接断开，3秒后重连...');
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          // 重新连接
        }
      }, 3000);
    };

    return () => {
      ws.close();
    };
  }, [user?.id, soundEnabled, fetchTicketData]);

  // ---- 心跳 ----

  useEffect(() => {
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // ---- 接单 ----

  const handleAccept = async (ticketId: number) => {
    try {
      await acceptTicket(ticketId);
      message.success('接单成功');
      fetchTicketData();

      // 通过 WebSocket 通知
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'accept_ticket',
          ticket_id: ticketId,
        }));
      }
    } catch {
      message.error('接单失败');
    }
  };

  // ---- 解决工单 ----

  const handleResolve = async (ticketId: number) => {
    try {
      await updateTicketStatus(ticketId, 'resolved');
      message.success('工单已解决');
      fetchTicketData();

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'resolve_ticket',
          ticket_id: ticketId,
        }));
      }
    } catch {
      message.error('操作失败');
    }
  };

  // ---- 表格列 ----

  const columns = [
    { title: '工单号', dataIndex: 'ticket_no', key: 'ticket_no', width: 120, render: (v: string) => <Text code>{v}</Text> },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '类型', dataIndex: 'ticket_type', key: 'ticket_type', width: 100, render: (t: string) => <Tag>{TYPE_LABELS[t] || t}</Tag> },
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80, render: (p: string) => <Tag color={PRIORITY_COLORS[p]}>{PRIORITY_LABELS[p]}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (s: string) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s]}</Tag> },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160, render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-' },
    {
      title: '操作', key: 'action', width: 160,
      render: (_: any, r: any) => (
        <Space>
          {r.status === 'pending' && (
            <Button type="primary" size="small" onClick={() => handleAccept(r.id)}>接单</Button>
          )}
          {r.status === 'processing' && (
            <Button type="primary" size="small" onClick={() => handleResolve(r.id)}>解决</Button>
          )}
          <Button type="link" size="small" onClick={() => navigate(`/cs/tickets/${r.id}`)}>详情</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>🎧 客服工作台</Title>
        <Space>
          <Badge count={newTicketCount} offset={[-2, 0]}>
            <Button icon={<SoundOutlined />} onClick={() => setSoundEnabled(!soundEnabled)}>
              {soundEnabled ? '提示音开' : '提示音关'}
            </Button>
          </Badge>
          <Tag color={connected ? 'green' : 'red'}>
            {connected ? '已连接' : '未连接'}
          </Tag>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card><Statistic title="待处理" value={stats.pending} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#f5222d' }} /></Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card><Statistic title="处理中" value={stats.processing} prefix={<ThunderboltOutlined />} valueStyle={{ color: '#1890ff' }} /></Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card><Statistic title="已解决" value={stats.resolved} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
      </Row>

      {/* 工单列表 */}
      <Card title="工单列表" extra={<Button onClick={fetchTicketData}>刷新</Button>}>
        <Table
          dataSource={tickets}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
};

export default WorkbenchPage;
