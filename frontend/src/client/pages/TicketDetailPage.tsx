/**
 * TicketDetailPage — 工单详情 + 实时聊天
 *
 * 用户端/客服端共用。
 * 上半部分: 工单信息
 * 下半部分: WebSocket 实时聊天窗口
 *
 * 客服端额外功能:
 * - AI 推荐回复按钮
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Tag, Typography, Button, Space, Spin, message, Tooltip } from 'antd';
import {
  ArrowLeftOutlined,
  RobotOutlined, CheckOutlined, MessageOutlined,
} from '@ant-design/icons';
import { getTicketDetail, suggestCSReply } from '@/shared/api/ticket';
import { useAppSelector } from '@/store/hooks';
import ChatWindow from '@/shared/components/ChatWindow';

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

  // AI 推荐回复
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState('');

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

  /** AI 推荐回复 */
  const handleAISuggest = async () => {
    setAiLoading(true);
    setAiSuggestion('');
    try {
      const res: any = await suggestCSReply(Number(id));
      setAiSuggestion(res.suggested_reply || '暂无推荐回复');
    } catch { message.error('AI 推荐失败'); }
    finally { setAiLoading(false); }
  };

  if (loading) return <Spin size="large" style={{ display: 'block', marginTop: 100, textAlign: 'center' }} />;
  if (!ticket) return <div>工单不存在</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: 'calc(100vh - 160px)' }}>
      {/* 工单信息头部 */}
      <Card size="small">
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} size="small">返回</Button>
            <Title level={5} style={{ margin: 0 }}>{ticket.ticket_no} — {ticket.title}</Title>
          </Space>
          <Space wrap size={4}>
            <Tag>{TYPE_LABELS[ticket.ticket_type] || ticket.ticket_type}</Tag>
            <Tag color={PRIORITY_COLORS[ticket.priority]}>{PRIORITY_LABELS[ticket.priority]}</Tag>
            <Tag color={STATUS_COLORS[ticket.status]}>{STATUS_LABELS[ticket.status]}</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              创建: {ticket.created_at ? new Date(ticket.created_at).toLocaleString('zh-CN') : '-'}
            </Text>
          </Space>
        </Space>
      </Card>

      {/* 主体: 问题描述 + 聊天 */}
      <div style={{ flex: 1, display: 'flex', gap: 16, minHeight: 0 }}>
        {/* 左侧: 问题描述 + AI 推荐 */}
        <div style={{ width: 320, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <Card size="small" title="问题描述" style={{ flex: 1, overflow: 'auto' }}>
            <Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 13 }}>
              {ticket.content}
            </Paragraph>
          </Card>

          {/* AI 推荐回复（仅客服端） */}
          {isCSAgent && (
            <Card size="small" title={<span><RobotOutlined /> AI 推荐</span>}>
              <Tooltip title="基于知识库 + 工单上下文生成推荐回复">
                <Button
                  icon={<RobotOutlined />}
                  onClick={handleAISuggest}
                  loading={aiLoading}
                  block
                  style={{ borderColor: '#722ed1', color: '#722ed1', fontWeight: 500 }}
                >
                  {aiLoading ? 'AI 生成中...' : 'AI 推荐回复'}
                </Button>
              </Tooltip>

              {aiSuggestion && (
                <div style={styles.aiSuggestion}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                    <RobotOutlined style={{ color: '#722ed1', marginRight: 6 }} />
                    <Text strong style={{ fontSize: 12, color: '#722ed1' }}>推荐回复</Text>
                  </div>
                  <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12, lineHeight: 1.5 }}>
                    {aiSuggestion}
                  </Paragraph>
                  <Button
                    type="link"
                    size="small"
                    icon={<CheckOutlined />}
                    onClick={() => {
                      navigator.clipboard.writeText(aiSuggestion);
                      message.success('已复制到剪贴板');
                    }}
                    style={{ padding: 0, fontSize: 11, marginTop: 4 }}
                  >
                    复制回复
                  </Button>
                </div>
              )}
            </Card>
          )}
        </div>

        {/* 右侧: 实时聊天窗口 */}
        <Card
          size="small"
          title={<span><MessageOutlined /> 实时聊天</span>}
          style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
          styles={{ body: { flex: 1, padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' } }}
        >
          <div style={{ flex: 1, minHeight: 0 }}>
            <ChatWindow
              ticketId={Number(id)}
              userId={user?.id || 0}
              userType={userType}
              ticketTitle={ticket.title}
            />
          </div>
        </Card>
      </div>
    </div>
  );
};

// ---- 样式 ----

const styles: Record<string, React.CSSProperties> = {
  aiSuggestion: {
    marginTop: 8,
    padding: '8px 10px',
    background: '#f9f0ff',
    borderRadius: 6,
    border: '1px solid #d3adf7',
  },
};

export default TicketDetailPage;
