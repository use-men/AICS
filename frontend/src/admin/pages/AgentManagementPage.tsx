/**
 * AgentManagementPage — 客服管理
 *
 * 功能:
 * - 查看所有客服账号
 * - 客服在线状态
 * - 客服工作负载
 * - 客服技能类型
 */

import { useState, useEffect } from 'react';
import {
  Card, Table, Tag, Typography, Space, Badge, Avatar, Tooltip, Button, message,
} from 'antd';
import {
  CustomerServiceOutlined, ReloadOutlined, WifiOutlined,
  DisconnectOutlined, CheckCircleOutlined, ClockCircleOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

interface Agent {
  id: number;
  user_id: number | null;
  name: string;
  employee_id: string;
  skill_type: string;
  current_ticket_count: number;
  max_ticket_count: number;
  online_status: string;
  is_active: boolean;
  user?: {
    id: number;
    username: string;
    nickname: string;
    avatar: string;
    employee_id: string;
  } | null;
}

const SKILL_TYPES: Record<string, { label: string; color: string }> = {
  all: { label: '全类型', color: 'purple' },
  after_sales: { label: '售后咨询', color: 'blue' },
  technical: { label: '技术支持', color: 'cyan' },
  refund: { label: '退款处理', color: 'orange' },
  complaint: { label: '投诉处理', color: 'red' },
};

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  online: { label: '在线', color: 'green', icon: <WifiOutlined /> },
  busy: { label: '忙碌', color: 'orange', icon: <ClockCircleOutlined /> },
  offline: { label: '离线', color: 'default', icon: <DisconnectOutlined /> },
};

const AgentManagementPage: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/v1/dispatch/agents', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAgents(data.agents || []);
      }
    } catch (error) {
      message.error('获取客服列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAgents(); }, []);

  // 统计数据
  const stats = {
    total: agents.length,
    online: agents.filter(a => a.online_status === 'online').length,
    busy: agents.filter(a => a.online_status === 'busy').length,
    offline: agents.filter(a => a.online_status === 'offline').length,
    totalTickets: agents.reduce((sum, a) => sum + (a.current_ticket_count || 0), 0),
  };

  const columns = [
    {
      title: '客服',
      key: 'agent',
      render: (_: any, record: Agent) => (
        <Space>
          <Avatar
            size={36}
            icon={<CustomerServiceOutlined />}
            src={record.user?.avatar}
            style={{
              backgroundColor: record.online_status === 'online' ? '#52c41a' :
                             record.online_status === 'busy' ? '#faad14' : '#d9d9d9',
            }}
          />
          <div>
            <div>
              <Text strong>{record.name}</Text>
              {record.user?.nickname && record.user.nickname !== record.name && (
                <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                  ({record.user.nickname})
                </Text>
              )}
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {record.user?.employee_id ? `工号: ${record.user.employee_id}` : record.user?.username || '未关联账号'}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'online_status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = STATUS_CONFIG[status] || STATUS_CONFIG.offline;
        return (
          <Badge status={status === 'online' ? 'success' : status === 'busy' ? 'warning' : 'default'}>
            <Tag color={config.color} icon={config.icon}>
              {config.label}
            </Tag>
          </Badge>
        );
      },
    },
    {
      title: '技能类型',
      dataIndex: 'skill_type',
      key: 'skill_type',
      width: 120,
      render: (type: string) => {
        const config = SKILL_TYPES[type] || { label: type, color: 'default' };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '工作负载',
      key: 'load',
      width: 150,
      render: (_: any, record: Agent) => {
        const current = record.current_ticket_count || 0;
        const max = record.max_ticket_count || 10;
        const percent = Math.round((current / max) * 100);
        const color = percent > 80 ? '#ff4d4f' : percent > 50 ? '#faad14' : '#52c41a';

        return (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Text style={{ fontSize: 12 }}>{current}/{max} 工单</Text>
              <Text style={{ fontSize: 12, color }}>{percent}%</Text>
            </div>
            <div style={{ height: 6, background: '#f0f0f0', borderRadius: 3 }}>
              <div style={{
                height: '100%',
                width: `${percent}%`,
                background: color,
                borderRadius: 3,
                transition: 'width 0.3s',
              }} />
            </div>
          </div>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'error'}>
          {active ? '启用' : '禁用'}
        </Tag>
      ),
    },
  ];

  return (
    <div>
      {/* 统计卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 16 }}>
        <Card size="small">
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>{stats.total}</div>
            <div style={{ color: '#666', fontSize: 12 }}>客服总数</div>
          </div>
        </Card>
        <Card size="small">
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>{stats.online}</div>
            <div style={{ color: '#666', fontSize: 12 }}>在线</div>
          </div>
        </Card>
        <Card size="small">
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>{stats.busy}</div>
            <div style={{ color: '#666', fontSize: 12 }}>忙碌</div>
          </div>
        </Card>
        <Card size="small">
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>{stats.totalTickets}</div>
            <div style={{ color: '#666', fontSize: 12 }}>处理中工单</div>
          </div>
        </Card>
      </div>

      {/* 客服列表 */}
      <Card
        title={
          <Space>
            <CustomerServiceOutlined />
            <span>客服列表</span>
          </Space>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchAgents} loading={loading}>
            刷新
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={agents}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default AgentManagementPage;
