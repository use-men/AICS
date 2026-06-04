/**
 * AgentRecommendations — 客服端 Agent 推荐组件
 *
 * 功能:
 * - 推荐回复
 * - 推荐工单分类
 * - 推荐优先级
 */

import { useState, useCallback } from 'react';
import { Card, Tag, Button, Typography, Space, Spin, Divider, message } from 'antd';
import {
  RobotOutlined, BulbOutlined, TagsOutlined, ThunderboltOutlined,
  CopyOutlined, CheckOutlined,
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;

// ---- 类型定义 ----

interface TicketClassification {
  ticket_type: string;
  ticket_type_name: string;
  confidence: number;
}

interface PriorityAnalysis {
  priority: string;
  reason: string;
}

interface KnowledgeAnswer {
  answer: string;
  sources: Array<{ content: string; score: number }>;
}

// ---- 优先级颜色映射 ----

const PRIORITY_COLORS: Record<string, string> = {
  urgent: '#f5222d',
  high: '#fa8c16',
  medium: '#1890ff',
  low: '#52c41a',
};

const PRIORITY_LABELS: Record<string, string> = {
  urgent: '紧急',
  high: '高',
  medium: '中',
  low: '低',
};

const TYPE_LABELS: Record<string, string> = {
  after_sales: '售后咨询',
  technical: '技术支持',
  refund: '退款申请',
  complaint: '投诉建议',
};

// ---- 主组件 ----

interface AgentRecommendationsProps {
  ticketTitle?: string;
  ticketContent?: string;
  onApplyReply?: (reply: string) => void;
  onApplyClassification?: (type: string) => void;
  onApplyPriority?: (priority: string) => void;
}

const AgentRecommendations: React.FC<AgentRecommendationsProps> = ({
  ticketTitle = '',
  ticketContent = '',
  onApplyReply,
  onApplyClassification,
  onApplyPriority,
}) => {
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [classification, setClassification] = useState<TicketClassification | null>(null);
  const [priority, setPriority] = useState<PriorityAnalysis | null>(null);
  const [knowledge, setKnowledge] = useState<KnowledgeAnswer | null>(null);
  const [copied, setCopied] = useState(false);

  const content = ticketContent || ticketTitle;

  // ---- 获取推荐分类 ----

  const fetchClassification = useCallback(async () => {
    if (!content) { message.warning('请先输入工单内容'); return; }
    setLoading((prev) => ({ ...prev, classify: true }));
    try {
      const res = await fetch('/api/v1/agent/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: ticketTitle || content.slice(0, 50), content }),
      });
      const data = await res.json();
      setClassification(data);
    } catch {
      message.error('分类分析失败');
    } finally {
      setLoading((prev) => ({ ...prev, classify: false }));
    }
  }, [content, ticketTitle]);

  // ---- 获取推荐优先级 ----

  const fetchPriority = useCallback(async () => {
    if (!content) { message.warning('请先输入工单内容'); return; }
    setLoading((prev) => ({ ...prev, priority: true }));
    try {
      const res = await fetch('/api/v1/agent/priority', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: ticketTitle || content.slice(0, 50), content }),
      });
      const data = await res.json();
      setPriority(data);
    } catch {
      message.error('优先级分析失败');
    } finally {
      setLoading((prev) => ({ ...prev, priority: false }));
    }
  }, [content, ticketTitle]);

  // ---- 获取推荐回复 ----

  const fetchKnowledge = useCallback(async () => {
    if (!content) { message.warning('请先输入工单内容'); return; }
    setLoading((prev) => ({ ...prev, knowledge: true }));
    try {
      const res = await fetch('/api/v1/agent/knowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: content }),
      });
      const data = await res.json();
      setKnowledge(data);
    } catch {
      message.error('知识检索失败');
    } finally {
      setLoading((prev) => ({ ...prev, knowledge: false }));
    }
  }, [content]);

  // ---- 一键分析 ----

  const fetchAll = useCallback(async () => {
    await Promise.all([fetchClassification(), fetchPriority(), fetchKnowledge()]);
  }, [fetchClassification, fetchPriority, fetchKnowledge]);

  // ---- 复制回复 ----

  const handleCopy = () => {
    if (knowledge?.answer) {
      navigator.clipboard.writeText(knowledge.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      message.success('已复制');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* 一键分析按钮 */}
      <Button
        type="primary"
        icon={<RobotOutlined />}
        onClick={fetchAll}
        loading={loading.classify || loading.priority || loading.knowledge}
        block
      >
        AI 智能分析
      </Button>

      {/* 推荐分类 */}
      <Card
        size="small"
        title={<><TagsOutlined /> 推荐分类</>}
        extra={
          <Button size="small" onClick={fetchClassification} loading={loading.classify}>
            重新分析
          </Button>
        }
      >
        {classification ? (
          <Space direction="vertical" size={4}>
            <Space>
              <Tag color="blue">{classification.ticket_type_name}</Tag>
              <Text type="secondary">置信度: {(classification.confidence * 100).toFixed(0)}%</Text>
            </Space>
            <Button
              size="small"
              type="link"
              onClick={() => onApplyClassification?.(classification.ticket_type)}
            >
              应用此分类
            </Button>
          </Space>
        ) : (
          <Text type="secondary">点击"重新分析"获取推荐分类</Text>
        )}
      </Card>

      {/* 推荐优先级 */}
      <Card
        size="small"
        title={<><ThunderboltOutlined /> 推荐优先级</>}
        extra={
          <Button size="small" onClick={fetchPriority} loading={loading.priority}>
            重新分析
          </Button>
        }
      >
        {priority ? (
          <Space direction="vertical" size={4}>
            <Space>
              <Tag color={PRIORITY_COLORS[priority.priority]}>
                {PRIORITY_LABELS[priority.priority] || priority.priority}
              </Tag>
              <Text type="secondary">{priority.reason}</Text>
            </Space>
            <Button
              size="small"
              type="link"
              onClick={() => onApplyPriority?.(priority.priority)}
            >
              应用此优先级
            </Button>
          </Space>
        ) : (
          <Text type="secondary">点击"重新分析"获取推荐优先级</Text>
        )}
      </Card>

      {/* 推荐回复 */}
      <Card
        size="small"
        title={<><BulbOutlined /> 推荐回复</>}
        extra={
          <Space>
            <Button size="small" onClick={fetchKnowledge} loading={loading.knowledge}>
              重新检索
            </Button>
            {knowledge?.answer && (
              <Button
                size="small"
                icon={copied ? <CheckOutlined /> : <CopyOutlined />}
                onClick={handleCopy}
              >
                {copied ? '已复制' : '复制'}
              </Button>
            )}
          </Space>
        }
      >
        {knowledge ? (
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Paragraph
              style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 13, background: '#f6ffed', padding: 8, borderRadius: 6 }}
            >
              {knowledge.answer}
            </Paragraph>
            {knowledge.sources.length > 0 && (
              <>
                <Divider style={{ margin: '4px 0' }} />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  来源: {knowledge.sources.length} 条知识库文档
                </Text>
              </>
            )}
            <Button
              size="small"
              type="link"
              onClick={() => onApplyReply?.(knowledge.answer)}
            >
              使用此回复
            </Button>
          </Space>
        ) : (
          <Text type="secondary">点击"重新检索"获取推荐回复</Text>
        )}
      </Card>
    </div>
  );
};

export default AgentRecommendations;
