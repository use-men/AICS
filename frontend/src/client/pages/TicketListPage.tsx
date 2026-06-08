/**
 * TicketListPage — 用户端工单列表
 */

import { useState, useEffect } from 'react';
import { Card, Table, Tag, Button, Space, Select, Badge, Modal, Form, Input, message, Popconfirm } from 'antd';
import { PlusOutlined, ReloadOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { fetchTickets, createTicket, deleteTicket, getUnreadCounts } from '@/shared/api/ticket';
import { useAppSelector } from '@/store/hooks';

const PRIORITY_COLORS: Record<string, string> = { urgent: 'red', high: 'orange', medium: 'blue', low: 'green' };
const PRIORITY_LABELS: Record<string, string> = { urgent: '紧急', high: '高', medium: '中', low: '低' };
const TYPE_LABELS: Record<string, string> = { after_sales: '售后咨询', technical: '技术支持', refund: '退款申请', complaint: '投诉建议' };
const STATUS_LABELS: Record<string, string> = { pending: '待分配', assigned: '已分配', processing: '处理中', resolved: '已解决', closed: '已关闭' };
const STATUS_COLORS: Record<string, string> = { pending: 'error', assigned: 'warning', processing: 'processing', resolved: 'success', closed: 'default' };

const TicketListPage: React.FC = () => {
  const navigate = useNavigate();
  const user = useAppSelector((s) => s.auth.user);
  const [tickets, setTickets] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [createOpen, setCreateOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [form] = Form.useForm();
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
          const unreadRes: any = await getUnreadCounts(ids, 'user');
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

  const handleDelete = async (id: number) => {
    try {
      await deleteTicket(id);
      message.success('工单已删除');
      fetchData();
    } catch {
      message.error('删除失败');
    }
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setCreateLoading(true);
      await createTicket(values);
      message.success('工单已创建');
      setCreateOpen(false);
      form.resetFields();
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error('创建失败');
    } finally { setCreateLoading(false); }
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
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80, render: (p: string) => <Tag color={PRIORITY_COLORS[p]}>{PRIORITY_LABELS[p] || p}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (s: string) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s] || s}</Tag> },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160, render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-' },
    { title: '操作', key: 'action', width: 120, render: (_: any, r: any) => (
      <Space>
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => navigate(`/tickets/${r.id}`)}>详情</Button>
        <Popconfirm title="确定删除此工单？" onConfirm={() => handleDelete(r.id)} okText="删除" cancelText="取消">
          <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      </Space>
    )},
  ];

  return (
    <Card
      title="我的工单"
      extra={
        <Space>
          <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={statusFilter} onChange={setStatusFilter}
            options={Object.entries(STATUS_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>创建工单</Button>
        </Space>
      }
    >
      <Table dataSource={tickets} columns={columns} rowKey="id" loading={loading}
        scroll={{ x: 800 }}
        pagination={{ current: page, total, pageSize: 10, onChange: setPage, showTotal: (t) => `共 ${t} 条` }} />

      <Modal title="创建工单" open={createOpen} onOk={handleCreate} onCancel={() => setCreateOpen(false)} confirmLoading={createLoading} okText="提交">
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true, message: '请输入标题' }]}>
            <Input placeholder="简要描述问题" maxLength={200} />
          </Form.Item>
          <Form.Item name="ticket_type" label="工单类型" rules={[{ required: true, message: '请选择类型' }]}>
            <Select placeholder="选择类型"
              options={Object.entries(TYPE_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
          <Form.Item name="content" label="详细描述" rules={[{ required: true, message: '请输入描述' }]}>
            <Input.TextArea rows={4} placeholder="详细描述您遇到的问题" maxLength={5000} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default TicketListPage;
