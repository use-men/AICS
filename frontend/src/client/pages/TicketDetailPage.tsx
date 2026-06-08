/**
 * TicketDetailPage — 工单详情 + 实时聊天
 *
 * 用户端/客服端共用。
 * 客服端：左侧工具栏 + 右侧聊天
 * 用户端：工单信息 + 提示
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Tag, Typography, Button, Space, Spin, message, Alert, Tabs } from 'antd';
import {
  ArrowLeftOutlined,
  RobotOutlined, MessageOutlined, InfoCircleOutlined,
  FileTextOutlined, ToolOutlined,
} from '@ant-design/icons';
import { getTicketDetail } from '@/shared/api/ticket';
import { useAppSelector } from '@/store/hooks';
import ChatWindow from '@/shared/components/ChatWindow';
import QuickReplies from '@/shared/components/QuickReplies';
import TicketStatusSwitcher from '@/shared/components/TicketStatusSwitcher';

const { Title, Text, Paragraph } = Typography;

const PRIORITY_COLORS: Record<string, string> = { urgent: 'red', high: 'orange', medium: 'blue', low: 'green' };
const PRIORITY_LABELS: Record<string, string> = { urgent: '紧急', high: '高', medium: '中', low: '低' };
const TYPE_LABELS: Record<string, string> = { after_sales: '售后咨询', technical: '技术支持', refund: '退款申请', complaint: '投诉建议' };
const STATUS_LABELS: Record<string, string> = { pending: '待分配', assigned: '已分配', processing: '处理中', resolved: '已解决', closed: '已关闭' };
const STATUS_COLORS: Record<string, string> = { pending: 'error', assigned: 'warning', processing: 'processing', resolved: 'success', closed: 'default' };

/** 客服角色码 */
const CS_ROLE_CODES = new Set(['customer_service', 'agent', 'supervisor']);

const TicketDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const user = useAppSelector((s) => s.auth.user);
  const [ticket, setTicket] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  /** 判断当前用户是否是客服端 */
  const isCSAgent = user?.roles?.some((r) => CS_ROLE_CODES.has(r)) ?? false;
  const userType: 'user' | 'service' = isCSAgent ? 'service' : 'user';

  const fetchDetail = async () => {
    setLoading(true);
    try {
      const data = await getTicketDetail(Number(id));
      setTicket(data);
    } catch { message.error('获取详情失败'); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchDetail(); }, [id]);

  /** 常用回复选择 */
  const handleQuickReplySelect = (content: string) => {
    window.dispatchEvent(new CustomEvent('quick-reply-select', { detail: content }));
  };

  /** 常用回复发送 */
  const handleQuickReplySend = (content: string) => {
    window.dispatchEvent(new CustomEvent('quick-reply-send', { detail: content }));
  };

  if (loading) return <Spin size="large" style={{ display: 'block', marginTop: 100, textAlign: 'center' }} />;
  if (!ticket) return <div>工单不存在</div>;

  // ==================== 用户端 ====================
  if (!isCSAgent) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: 'calc(100vh - 160px)' }}>
        {/* 头部 */}
        <Card size="small" style={{ background: '#fff' }}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} size="small">返回</Button>
            <Title level={5} style={{ margin: 0 }}>{ticket.ticket_no} — {ticket.title}</Title>
          </Space>
          <Space wrap size={4} style={{ marginTop: 8 }}>
            <Tag>{TYPE_LABELS[ticket.ticket_type] || ticket.ticket_type}</Tag>
            <Tag color={PRIORITY_COLORS[ticket.priority]}>{PRIORITY_LABELS[ticket.priority]}</Tag>
            <Tag color={STATUS_COLORS[ticket.status]}>{STATUS_LABELS[ticket.status]}</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              创建: {ticket.created_at ? new Date(ticket.created_at).toLocaleString('zh-CN') : '-'}
            </Text>
          </Space>
        </Card>

        {/* 问题描述 */}
        <Card size="small" title="问题描述" style={{ flex: 1 }}>
          <Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 14, lineHeight: 1.8 }}>
            {ticket.content}
          </Paragraph>
        </Card>

        {/* 提示 */}
        <Alert
          message="如需与客服沟通，请通过 AI 对话界面发起"
          description={
            <Button
              type="link"
              icon={<RobotOutlined />}
              onClick={() => navigate('/chat')}
              style={{ padding: 0, marginTop: 4 }}
            >
              前往 AI 对话
            </Button>
          }
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
        />
      </div>
    );
  }

  // ==================== 客服端 ====================
  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 160px)', gap: 0, background: '#f0f2f5', borderRadius: 8, overflow: 'hidden' }}>
      {/* 左侧工具栏 */}
      <div style={{ width: 300, flexShrink: 0, display: 'flex', flexDirection: 'column', background: '#fff', borderRight: '1px solid #e8e8e8' }}>
        {/* 工单信息卡片 */}
        <div style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', padding: '12px 16px' }}>
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate(-1)}
              size="small"
              style={{ color: '#fff', borderColor: 'rgba(255,255,255,0.3)', background: 'transparent' }}
            >
              返回
            </Button>
          </Space>
          <div style={{ marginTop: 8 }}>
            <Title level={5} style={{ margin: 0, color: '#fff', fontSize: 15 }}>{ticket.ticket_no}</Title>
            <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12 }}>{ticket.title}</Text>
          </div>
          <Space wrap size={4} style={{ marginTop: 8 }}>
            <Tag style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', border: 'none', fontSize: 11 }}>
              {TYPE_LABELS[ticket.ticket_type]}
            </Tag>
            <Tag style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', border: 'none', fontSize: 11 }}>
              {PRIORITY_LABELS[ticket.priority]}
            </Tag>
          </Space>
        </div>

        {/* 工单状态 */}
        <div style={{ padding: '12px', borderBottom: '1px solid #f0f0f0' }}>
          <TicketStatusSwitcher
            ticketId={ticket.id}
            currentStatus={ticket.status}
            onStatusChange={(newStatus) => {
              setTicket({ ...ticket, status: newStatus });
            }}
            style={{ border: 'none', boxShadow: 'none' }}
          />
        </div>

        {/* 问题描述 */}
        <div style={{ padding: '12px', borderBottom: '1px solid #f0f0f0', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <FileTextOutlined style={{ color: '#666', fontSize: 12 }} />
            <Text strong style={{ fontSize: 12, color: '#666' }}>问题描述</Text>
          </div>
          <Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 12, lineHeight: 1.5, color: '#333', maxHeight: 100, overflow: 'auto' }}>
            {ticket.content}
          </Paragraph>
        </div>

        {/* 常用回复 */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <QuickReplies
            onSelect={handleQuickReplySelect}
            onSend={handleQuickReplySend}
            style={{ height: '100%', border: 'none', borderRadius: 0 }}
          />
        </div>
      </div>

      {/* 右侧聊天区域 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#fff' }}>
        {/* 聊天头部 */}
        <div style={{ padding: '10px 16px', borderBottom: '1px solid #e8e8e8', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <MessageOutlined style={{ color: '#666' }} />
            <Text strong style={{ fontSize: 13 }}>实时聊天</Text>
          </Space>
          <Tag color="green" style={{ fontSize: 11 }}>在线</Tag>
        </div>

        {/* 聊天内容 */}
        <div style={{ flex: 1, minHeight: 0 }}>
          <ChatWindow
            ticketId={Number(id)}
            userId={user?.id || 0}
            userType={userType}
            ticketTitle={ticket.title}
          />
        </div>
      </div>
    </div>
  );
};

export default TicketDetailPage;
