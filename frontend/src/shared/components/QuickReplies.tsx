/**
 * QuickReplies — 常用回复模板组件
 *
 * 功能:
 * - 预设常用回复话术
 * - 一键复制/发送
 * - 分类管理
 */

import { useState } from 'react';
import { Card, Button, Typography, Tag, Space, Tooltip, message as antMessage } from 'antd';
import {
  CopyOutlined, SendOutlined, SmileOutlined,
  FileTextOutlined, CustomerServiceOutlined, QuestionCircleOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

// ---- 常用回复模板数据 ----

interface QuickReply {
  id: number;
  category: string;
  title: string;
  content: string;
}

const DEFAULT_REPLIES: QuickReply[] = [
  // 问候类
  { id: 1, category: '问候', title: '开场问候', content: '您好！感谢您的咨询。请问有什么可以帮助您的？' },
  { id: 2, category: '问候', title: '等待回复', content: '您好，请问还有其他问题吗？我随时为您服务。' },

  // 问题处理类
  { id: 3, category: '处理', title: '已记录问题', content: '已记录您的问题，我们会尽快为您处理，请耐心等待。' },
  { id: 4, category: '处理', title: '需要更多信息', content: '为了更好地帮助您，请提供以下信息：\n1. 订单号\n2. 问题截图\n3. 联系方式' },
  { id: 5, category: '处理', title: '转交处理', content: '您的问题已转交相关部门处理，预计 1-2 个工作日内回复您。' },

  // 结束类
  { id: 6, category: '结束', title: '问题已解决', content: '很高兴能帮到您！如果后续有任何问题，随时联系我们。祝您生活愉快！' },
  { id: 7, category: '结束', title: '满意度评价', content: '感谢您的咨询，请对本次服务进行评价，您的反馈是我们改进的动力。' },

  // 特殊场景
  { id: 8, category: '场景', title: '退款进度', content: '您的退款申请已提交，预计 3-5 个工作日到账，请注意查收。' },
  { id: 9, category: '场景', title: '物流查询', content: '您的包裹已发出，物流单号为：______，预计 ______ 天内送达。' },
  { id: 10, category: '场景', title: '技术问题', content: '请尝试以下步骤：\n1. 清除浏览器缓存\n2. 重新登录\n3. 如仍无法解决，请联系我们' },
];

const CATEGORY_COLORS: Record<string, string> = {
  '问候': 'blue',
  '处理': 'orange',
  '结束': 'green',
  '场景': 'purple',
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  '问候': <SmileOutlined />,
  '处理': <FileTextOutlined />,
  '结束': <CustomerServiceOutlined />,
  '场景': <QuestionCircleOutlined />,
};

// ---- Props ----

interface QuickRepliesProps {
  onSelect?: (content: string) => void;
  onSend?: (content: string) => void;
  style?: React.CSSProperties;
}

// ---- 组件 ----

const QuickReplies: React.FC<QuickRepliesProps> = ({
  onSelect,
  onSend,
  style,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('全部');
  const [replies] = useState<QuickReply[]>(DEFAULT_REPLIES);

  const categories = ['全部', ...new Set(replies.map(r => r.category))];
  const filteredReplies = selectedCategory === '全部'
    ? replies
    : replies.filter(r => r.category === selectedCategory);

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
    antMessage.success('已复制到剪贴板');
  };

  const handleSelect = (content: string) => {
    onSelect?.(content);
    antMessage.info('已填入输入框');
  };

  const handleSend = (content: string) => {
    onSend?.(content);
    antMessage.success('已发送');
  };

  return (
    <div style={{ ...style, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 标题栏 */}
      <div style={{ padding: '10px 12px', borderBottom: '1px solid #f0f0f0', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
          <FileTextOutlined style={{ color: '#666', fontSize: 12 }} />
          <Text strong style={{ fontSize: 12, color: '#666' }}>常用回复</Text>
        </div>
        {/* 分类标签 */}
        <Space size={4} wrap>
          {categories.map(cat => (
            <Tag
              key={cat}
              color={selectedCategory === cat ? 'blue' : undefined}
              style={{ cursor: 'pointer', fontSize: 11, padding: '0 6px', margin: 0 }}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </Tag>
          ))}
        </Space>
      </div>

      {/* 回复列表 */}
      <div style={{ flex: 1, overflow: 'auto', padding: '8px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {filteredReplies.map(reply => (
            <div
              key={reply.id}
              style={{
                padding: '6px 8px',
                background: '#fafafa',
                borderRadius: 4,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#f0f5ff';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#fafafa';
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, minWidth: 0, flex: 1 }}>
                  <Tag color={CATEGORY_COLORS[reply.category]} style={{ fontSize: 10, padding: '0 4px', margin: 0 }}>
                    {reply.category}
                  </Tag>
                  <Text strong style={{ fontSize: 12 }} ellipsis>{reply.title}</Text>
                </div>
                <Space size={2} style={{ flexShrink: 0 }}>
                  <Button
                    type="text"
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={(e) => { e.stopPropagation(); handleCopy(reply.content); }}
                    style={{ fontSize: 11, color: '#999', padding: '0 4px' }}
                  />
                  <Button
                    type="text"
                    size="small"
                    icon={<SendOutlined />}
                    onClick={(e) => { e.stopPropagation(); handleSelect(reply.content); }}
                    style={{ fontSize: 11, color: '#1890ff', padding: '0 4px' }}
                  />
                </Space>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default QuickReplies;
