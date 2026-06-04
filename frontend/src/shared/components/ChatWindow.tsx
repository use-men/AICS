/**
 * ChatWindow — 实时聊天窗口组件
 *
 * 功能:
 * - ChatGPT 风格 UI
 * - 文本/图片/文件消息
 * - 在线状态
 * - 未读消息
 * - 已读状态
 */

import { useState, useRef, useEffect } from 'react';
import { Input, Button, Typography, Avatar, Badge, Tag, Upload, message as antMessage } from 'antd';
import {
  SendOutlined, UserOutlined, CustomerServiceOutlined,
  CheckOutlined, CheckCircleOutlined, PictureOutlined, FileOutlined,
  WifiOutlined, DisconnectOutlined,
} from '@ant-design/icons';
import { useChat, ChatMessage } from '@/shared/hooks/useChat';

const { Text } = Typography;

// ---- Props ----

interface ChatWindowProps {
  ticketId: number;
  userId: number;
  userType: 'user' | 'service';
  ticketTitle?: string;
}

// ---- 组件 ----

const ChatWindow: React.FC<ChatWindowProps> = ({
  ticketId,
  userId,
  userType,
  ticketTitle,
}) => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    connected,
    onlineCount,
    unreadCount,
    sendMessage,
    markRead,
  } = useChat({
    ticketId,
    userId,
    userType,
    onNewMessage: (msg) => {
      // 收到消息时自动标记已读
      if (msg.sender_type !== userType) {
        markRead();
      }
    },
  });

  // 打开聊天时标记所有消息为已读
  useEffect(() => {
    if (messages.length > 0 && connected) {
      markRead();
    }
  }, [messages.length, connected]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ---- 发送消息 ----

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text) return;
    sendMessage(text, 'text');
    setInputValue('');
  };

  // ---- 渲染消息 ----

  const renderMessage = (msg: ChatMessage) => {
    const isMe = msg.sender_type === userType;
    const isAI = msg.sender_type === 'ai';

    return (
      <div
        key={msg.id}
        style={{
          display: 'flex',
          justifyContent: isMe ? 'flex-end' : 'flex-start',
          marginBottom: 12,
          gap: 8,
        }}
      >
        {/* 对方头像 */}
        {!isMe && (
          <Avatar
            size={32}
            icon={msg.sender_type === 'service' ? <CustomerServiceOutlined /> : <UserOutlined />}
            style={{
              backgroundColor: isAI ? '#722ed1' : msg.sender_type === 'service' ? '#52c41a' : '#667eea',
              flexShrink: 0,
            }}
          />
        )}

        {/* 消息气泡 */}
        <div style={{ maxWidth: '70%' }}>
          {/* 发送者名称 */}
          <div style={{
            display: 'flex',
            justifyContent: isMe ? 'flex-end' : 'flex-start',
            gap: 4,
            marginBottom: 2,
          }}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {isMe ? '我' : msg.sender_type === 'service' ? '客服' : msg.sender_type === 'ai' ? 'AI' : '用户'}
            </Text>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {msg.created_at ? new Date(msg.created_at).toLocaleTimeString('zh-CN') : ''}
            </Text>
          </div>

          {/* 消息内容 */}
          <div style={{
            padding: '8px 12px',
            borderRadius: isMe ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
            backgroundColor: isMe ? '#667eea' : isAI ? '#f5f0ff' : '#f0f2f5',
            color: isMe ? '#fff' : '#333',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}>
            {msg.message_type === 'image' ? (
              <img src={msg.content} alt="图片" style={{ maxWidth: 200, borderRadius: 8 }} />
            ) : msg.message_type === 'file' ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <FileOutlined />
                <span>{msg.content}</span>
              </div>
            ) : (
              msg.content
            )}
          </div>

          {/* 已读状态 */}
          {isMe && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 2 }}>
              {msg.is_read ? (
                <CheckCircleOutlined style={{ fontSize: 12, color: '#52c41a' }} />
              ) : (
                <CheckOutlined style={{ fontSize: 12, color: '#bbb' }} />
              )}
            </div>
          )}
        </div>

        {/* 我的头像 */}
        {isMe && (
          <Avatar
            size={32}
            icon={<UserOutlined />}
            style={{ backgroundColor: '#667eea', flexShrink: 0 }}
          />
        )}
      </div>
    );
  };

  return (
    <div style={styles.container}>
      {/* 头部 */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <Text strong>{ticketTitle || `工单 #${ticketId}`}</Text>
        </div>
        <div style={styles.headerRight}>
          <Badge count={unreadCount} offset={[-2, 0]}>
            <Tag>{unreadCount} 未读</Tag>
          </Badge>
          <Tag icon={connected ? <WifiOutlined /> : <DisconnectOutlined />} color={connected ? 'green' : 'red'}>
            {connected ? '已连接' : '未连接'}
          </Tag>
          <Tag>{onlineCount} 人在线</Tag>
        </div>
      </div>

      {/* 消息区域 */}
      <div style={styles.messagesContainer}>
        {messages.length === 0 ? (
          <div style={styles.emptyState}>
            <Text type="secondary">暂无消息，开始对话吧</Text>
          </div>
        ) : (
          messages.map(renderMessage)
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div style={styles.inputContainer}>
        <Input.Group compact style={{ display: 'flex' }}>
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="输入消息... (Enter 发送)"
            style={{ flex: 1 }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            disabled={!inputValue.trim() || !connected}
          >
            发送
          </Button>
        </Input.Group>
      </div>
    </div>
  );
};

// ---- 样式 ----

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    border: '1px solid #e8e8e8',
    borderRadius: 8,
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 16px',
    borderBottom: '1px solid #f0f0f0',
    background: '#fafafa',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  messagesContainer: {
    flex: 1,
    overflow: 'auto',
    padding: 16,
  },
  emptyState: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100%',
  },
  inputContainer: {
    padding: '12px 16px',
    borderTop: '1px solid #f0f0f0',
    background: '#fafafa',
  },
};

export default ChatWindow;
