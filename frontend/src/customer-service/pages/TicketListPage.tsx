/**
 * CSTicketListPage — 客服端工单列表（含未读消息提示）
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, Table, Tag, Button, Space, Select, Badge, message } from 'antd';
import { ReloadOutlined, EyeOutlined, CheckOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { fetchTickets, acceptTicket, updateTicketStatus, getUnreadCounts } from '@/shared/api/ticket';
import { useAppSelector } from '@/store/hooks';

const PRIORITY_COLORS: Record<string, string> = { urgent: 'red', high: 'orange', medium: 'blue', low: 'green' };
const PRIORITY_LABELS: Record<string, string> = { urgent: '紧急', high: '高', medium: '中', low: '低' };
const TYPE_LABELS: Record<string, string> = { after_sales: '售后咨询', technical: '技术支持', refund: '退款申请', complaint: '投诉建议' };
const STATUS_LABELS: Record<string, string> = { pending: '待分配', assigned: '已分配', processing: '处理中', resolved: '已解决', closed: '已关闭' };
const STATUS_COLORS: Record<string, string> = { pending: 'error', assigned: 'warning', processing: 'processing', resolved: 'success', closed: 'default' };

const CSTicketListPage: React.FC = () => {
  const navigate = useNavigate();
  const user = useAppSelector((s) => s.auth.user);
  const [tickets, setTickets] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [unreadMap, setUnreadMap] = useState<Record<number, number>>({});

  const fetchData = async () => {
    setLoading(true);
    try {
      const res: any = await fetchTickets({ page, status: statusFilter });
      const ticketList = res.data || [];
      setTickets(ticketList);
      setTotal(res.total || 0);

      // 批量查询未读消息数
      if (ticketList.length > 0 && user?.id) {
        try {
          const ids = ticketList.map((t: any) => t.id);
          const unreadRes: any = await getUnreadCounts(ids, 'service');
          const counts: Record<number, number> = {};
          const raw = unreadRes?.unread_counts || {};
          for (const [key, val] of Object.entries(raw)) {
            counts[Number(key)] = val as number;
          }
          setUnreadMap(counts);
        } catch {}
      }
    } catch { message.error('获取失败'); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, [page, statusFilter]);

  // 从工单详情返回时刷新（窗口获得焦点）
  useEffect(() => {
    const handleFocus = () => fetchData();
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [page, statusFilter]);

  // 定时刷新未读数
  useEffect(() => {
    const timer = setInterval(() => {
      if (tickets.length > 0 && user?.id) {
        getUnreadCounts(tickets.map((t: any) => t.id), 'service')
          .then((res: any) => {
            const counts: Record<number, number> = {};
            const raw = res?.unread_counts || {};
            for (const [key, val] of Object.entries(raw)) {
              counts[Number(key)] = val as number;
            }
            setUnreadMap(counts);
          })
          .catch(() => {});
      }
    }, 15000); // 每15秒刷新
    return () => clearInterval(timer);
  }, [tickets, user?.id]);

  const handleAccept = async (id: number) => {
    try {
      await acceptTicket(id);
      message.success('接单成功');
      fetchData();
    } catch { message.error('接单失败'); }
  };

  const handleStatusChange = async (id: number, status: string) => {
    try {
      await updateTicketStatus(id, status);
      message.success('状态已更新');
      fetchData();
    } catch { message.error('更新失败'); }
  };

  const columns = [
    {
      title: '工单号', dataIndex: 'ticket_no', key: 'ticket_no', width: 120,
      render: (v: string, r: any) => {
        const unread = unreadMap[r.id] || 0;
        return (
          <Space>
            <span style={{ fontFamily: 'monospace' }}>{v}</span>
            {unread > 0 && <Badge count={unread} size="small" />}
          </Space>
        );
      },
    },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '类型', dataIndex: 'ticket_type', key: 'ticket_type', width: 100, render: (t: string) => <Tag>{TYPE_LABELS[t] || t}</Tag> },
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80, render: (p: string) => <Tag color={PRIORITY_COLORS[p]}>{PRIORITY_LABELS[p]}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (s: string) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s]}</Tag> },
    { title: '回复', dataIndex: 'reply_count', key: 'reply_count', width: 60, render: (v: number) => v || 0 },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160, render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-' },
    {
      title: '操作', key: 'action', width: 160,
      render: (_: any, r: any) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => navigate(`/cs/tickets/${r.id}`)}>详情</Button>
          {r.status === 'pending' && (
            <Button type="link" size="small" icon={<CheckOutlined />} onClick={() => handleAccept(r.id)}>接单</Button>
          )}
          {r.status === 'processing' && (
            <Button type="link" size="small" onClick={() => handleStatusChange(r.id, 'resolved')}>解决</Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="工单列表"
      extra={
        <Space>
          <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={statusFilter} onChange={setStatusFilter}
            options={Object.entries(STATUS_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
        </Space>
      }
    >
      <Table dataSource={tickets} columns={columns} rowKey="id" loading={loading}
        scroll={{ x: 900 }}
        pagination={{ current: page, total, pageSize: 10, onChange: setPage, showTotal: (t) => `共 ${t} 条` }} />
    </Card>
  );
};

export default CSTicketListPage;
