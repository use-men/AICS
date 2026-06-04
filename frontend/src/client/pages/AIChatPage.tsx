/**
 * AIChatPage — ChatGPT 风格 AI 客服聊天界面
 *
 * 功能:
 * - ChatGPT 风格 UI
 * - 流式输出（SSE）
 * - 多轮对话
 * - 历史上下文
 * - 引用来源展示
 * - 转人工按钮
 *
 * 消息状态存储在 Redux (chat slice)，页面切换后不会丢失。
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Button, Input, Typography, Spin, message, Tag, Tooltip } from 'antd';
import {
  SendOutlined, RobotOutlined, UserOutlined, CustomerServiceOutlined,
  ClearOutlined, CopyOutlined, FileTextOutlined,
} from '@ant-design/icons';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import {
  addMessage, updateMessage, clearMessages, setConversationId,
} from '@/store/slices/chatSlice';
import type { ChatMessage } from '@/store/slices/chatSlice';

const { Text } = Typography;

// ---- 主组件 ----

const AIChatPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const messages = useAppSelector((s) => s.chat.messages);
  const conversationId = useAppSelector((s) => s.chat.conversationId);

  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);

  // 确保 conversationId 存在
  useEffect(() => {
    if (!conversationId) {
      dispatch(setConversationId(`chat_${user?.id || 'guest'}_${Date.now()}`));
    }
  }, [conversationId, dispatch, user?.id]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 聚焦输入框
  useEffect(() => {
    inputRef.current?.focus();
  }, [loading]);

  // ---- 发送消息（流式） ----

  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || loading) return;

    const convId = conversationId || `chat_${user?.id || 'guest'}_${Date.now()}`;
    if (!conversationId) {
      dispatch(setConversationId(convId));
    }

    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
      status: 'done',
    };

    const assistantMsg: ChatMessage = {
      id: `assistant_${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      status: 'streaming',
    };

    dispatch(addMessage(userMsg));
    dispatch(addMessage(assistantMsg));
    setInputValue('');
    setLoading(true);

    try {
      const res = await fetch('/api/v1/agent/cs/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          conversation_id: convId,
          user_id: user?.id,
        }),
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      let sources: Array<{ question: string; answer: string; score: number }> = [];
      let needHuman = false;
      let transferInfo: ChatMessage['transferInfo'] = undefined;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);

              if (parsed.type === 'delta' && parsed.content) {
                fullContent += parsed.content;
                dispatch(updateMessage({
                  ...assistantMsg,
                  content: fullContent,
                  status: 'streaming',
                }));
              }

              if (parsed.type === 'sources') {
                sources = parsed.sources || [];
              }

              if (parsed.type === 'done') {
                needHuman = parsed.need_human || false;
                sources = parsed.sources || sources;
                // 用后端清理后的内容覆盖（去除 [TRANSFER_TO_HUMAN] 等标记）
                if (parsed.content) {
                  fullContent = parsed.content;
                }
              }

              // 后端自动转人工结果
              if (parsed.type === 'transfer') {
                transferInfo = {
                  ticket_id: parsed.ticket_id,
                  ticket_no: parsed.ticket_no,
                  title: parsed.title,
                  ticket_type: parsed.ticket_type,
                  type_name: parsed.type_name,
                  priority: parsed.priority,
                  service_id: parsed.service_id,
                  service_name: parsed.service_name,
                };
              }
            } catch {}
          }
        }
      }

      // 如果流式没返回内容，使用非流式 API
      if (!fullContent) {
        const fallback = await fetch('/api/v1/agent/cs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            conversation_id: convId,
            user_id: user?.id,
          }),
        });
        const result = await fallback.json();
        fullContent = result.answer || '抱歉，暂时无法回答';
        sources = result.sources || [];
        needHuman = result.need_human || false;
      }

      // 更新最终消息（含转人工信息）
      dispatch(updateMessage({
        ...assistantMsg,
        content: fullContent,
        sources,
        needHuman,
        transferInfo,
        status: 'done',
      }));

      // 自动转人工后，追加系统提示消息
      if (needHuman && transferInfo) {
        const serviceName = transferInfo.service_name || '排队中';
        dispatch(addMessage({
          id: `system_transfer_${Date.now()}`,
          role: 'system',
          content: `🔄 已自动创建工单 ${transferInfo.ticket_no}，正在转接人工客服（${serviceName}），请稍候...`,
          timestamp: Date.now(),
          status: 'done',
        }));
      }
    } catch (err) {
      dispatch(updateMessage({
        ...assistantMsg,
        content: '抱歉，AI客服暂时不可用，请稍后再试。',
        status: 'error',
      }));
    } finally {
      setLoading(false);
    }
  }, [inputValue, loading, user?.id, conversationId, dispatch]);

  // ---- 转人工 ----

  const handleTransferHuman = async () => {
    const userMessages = messages.filter((m) => m.role === 'user').map((m) => m.content).join('\n');
    if (!userMessages) return;

    try {
      // 1. 创建工单
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/v1/agent/create-ticket', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          content: userMessages,
          conversation_id: conversationId,
          user_id: user?.id,
        }),
      });
      const result = await res.json();

      if (result.ticket_id) {
        // 2. 自动派单
        let serviceInfo = '';
        try {
          const token = localStorage.getItem('access_token');
          const dispatchRes = await fetch('/api/v1/dispatch/auto', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
              ticket_id: result.ticket_id,
              ticket_type: result.ticket_type || 'after_sales',
            }),
          });
          const dispatchData = await dispatchRes.json();
          if (dispatchData.service_name) {
            serviceInfo = `\n已分配给客服: ${dispatchData.service_name}`;
          }
        } catch {}

        dispatch(addMessage({
          id: `system_${Date.now()}`,
          role: 'system',
          content: `✅ 工单已创建: ${result.ticket_id}（${result.ticket_type}）${serviceInfo}\n\n正在为您转接人工客服，请稍候...`,
          timestamp: Date.now(),
          status: 'done',
        }));
        message.success('工单已创建，正在转接人工客服');
      }
    } catch {
      message.error('转人工失败，请稍后再试');
    }
  };

  // ---- 清空对话 ----

  const handleClear = () => {
    dispatch(clearMessages());
    dispatch(setConversationId(`chat_${user?.id || 'guest'}_${Date.now()}`));
  };

  // ---- 复制消息 ----

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
    message.success('已复制');
  };

  // ---- 渲染消息内容（支持 Markdown 简单格式） ----

  const renderContent = (content: string) => {
    return content.split('\n').map((line, i) => {
      // 粗体
      line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      // 行内代码
      line = line.replace(/`(.*?)`/g, '<code style="background:#f5f5f5;padding:2px 6px;border-radius:4px">$1</code>');
      return (
        <div
          key={i}
          style={{ margin: i === 0 ? 0 : '4px 0', fontSize: 14, lineHeight: 1.6 }}
          dangerouslySetInnerHTML={{ __html: line || '&nbsp;' }}
        />
      );
    });
  };

  // ---- 渲染 ----

  return (
    <div style={styles.container}>
      {/* 消息区域 */}
      <div style={styles.messagesContainer}>
        {messages.map((msg) => (
          <div key={msg.id} style={styles.messageWrapper}>
            {/* 头像 */}
            <div style={styles.avatarContainer}>
              {msg.role === 'user' ? (
                <div style={{ ...styles.avatar, background: '#667eea' }}>
                  <UserOutlined style={{ color: '#fff', fontSize: 16 }} />
                </div>
              ) : msg.role === 'system' ? (
                <div style={{ ...styles.avatar, background: '#52c41a' }}>
                  <FileTextOutlined style={{ color: '#fff', fontSize: 16 }} />
                </div>
              ) : (
                <div style={{ ...styles.avatar, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
                  <RobotOutlined style={{ color: '#fff', fontSize: 16 }} />
                </div>
              )}
            </div>

            {/* 消息内容 */}
            <div style={styles.messageContent}>
              <div style={styles.messageHeader}>
                <Text strong style={{ fontSize: 13 }}>
                  {msg.role === 'user' ? '你' : msg.role === 'system' ? '系统' : 'SmartDesk AI'}
                </Text>
                <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
                  {new Date(msg.timestamp).toLocaleTimeString('zh-CN')}
                </Text>
              </div>

              <div style={styles.messageBody}>
                {msg.status === 'streaming' && !msg.content ? (
                  <Spin size="small" />
                ) : (
                  renderContent(msg.content)
                )}
                {msg.status === 'streaming' && msg.content && (
                  <span style={styles.cursor}>▊</span>
                )}
              </div>

              {/* 引用来源 */}
              {msg.sources && msg.sources.length > 0 && msg.status === 'done' && (
                <div style={styles.sourcesContainer}>
                  <Text type="secondary" style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>
                    📚 参考来源:
                  </Text>
                  <div style={styles.sourcesList}>
                    {msg.sources.slice(0, 3).map((s, i) => (
                      <Tooltip key={i} title={s.answer} placement="top">
                        <Tag style={styles.sourceTag}>
                          {i + 1}. {s.question.slice(0, 20)}...
                          <Text type="secondary" style={{ fontSize: 10, marginLeft: 4 }}>
                            {(s.score * 100).toFixed(0)}%
                          </Text>
                        </Tag>
                      </Tooltip>
                    ))}
                  </div>
                </div>
              )}

              {/* 转人工工单信息 */}
              {msg.transferInfo && (
                <div style={styles.transferContainer}>
                  <div style={styles.transferHeader}>
                    <CustomerServiceOutlined style={{ color: '#1890ff', marginRight: 6 }} />
                    <Text strong style={{ fontSize: 13, color: '#1890ff' }}>已自动转人工</Text>
                  </div>
                  <div style={styles.transferBody}>
                    <div><Text type="secondary" style={{ fontSize: 12 }}>工单号: </Text><Text style={{ fontSize: 12 }}>{msg.transferInfo.ticket_no}</Text></div>
                    <div><Text type="secondary" style={{ fontSize: 12 }}>类型: </Text><Text style={{ fontSize: 12 }}>{msg.transferInfo.type_name}</Text></div>
                    <div><Text type="secondary" style={{ fontSize: 12 }}>优先级: </Text><Tag color={msg.transferInfo.priority === 'urgent' ? 'red' : msg.transferInfo.priority === 'high' ? 'orange' : 'blue'} style={{ fontSize: 11 }}>{msg.transferInfo.priority}</Tag></div>
                    {msg.transferInfo.service_name && (
                      <div><Text type="secondary" style={{ fontSize: 12 }}>分配客服: </Text><Text strong style={{ fontSize: 12 }}>{msg.transferInfo.service_name}</Text></div>
                    )}
                  </div>
                </div>
              )}

              {/* 操作按钮 */}
              {msg.role === 'assistant' && msg.status === 'done' && msg.content && (
                <div style={styles.actions}>
                  <Tooltip title="复制">
                    <Button type="text" size="small" icon={<CopyOutlined />} onClick={() => handleCopy(msg.content)} />
                  </Tooltip>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div style={styles.inputContainer}>
        <div style={styles.inputWrapper}>
          <Input.TextArea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={styles.input}
            disabled={loading}
          />
          <div style={styles.inputActions}>
            <Button
              icon={<ClearOutlined />}
              onClick={handleClear}
              size="small"
              disabled={loading}
            >
              清空
            </Button>
            <Button
              icon={<CustomerServiceOutlined />}
              onClick={handleTransferHuman}
              size="small"
              disabled={loading || messages.some((m) => m.transferInfo)}
            >
              {messages.some((m) => m.transferInfo) ? '已转人工' : '转人工'}
            </Button>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={loading}
              size="small"
            >
              发送
            </Button>
          </div>
        </div>
        <Text type="secondary" style={{ fontSize: 11, textAlign: 'center', marginTop: 8 }}>
          SmartDesk AI 客服 · 基于知识库的智能问答
        </Text>
      </div>
    </div>
  );
};

// ---- 样式 ----

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: 'calc(100vh - 160px)',
    background: '#fff',
    borderRadius: 12,
    overflow: 'hidden',
    border: '1px solid #e8e8e8',
  },
  messagesContainer: {
    flex: 1,
    overflow: 'auto',
    padding: '20px 0',
  },
  messageWrapper: {
    display: 'flex',
    padding: '16px 24px',
    gap: 16,
  },
  avatarContainer: {
    flexShrink: 0,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  messageContent: {
    flex: 1,
    minWidth: 0,
  },
  messageHeader: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: 4,
  },
  messageBody: {
    fontSize: 14,
    lineHeight: 1.6,
    color: '#333',
  },
  cursor: {
    animation: 'blink 1s infinite',
    color: '#667eea',
  },
  sourcesContainer: {
    marginTop: 8,
    padding: '8px 12px',
    background: '#f9f9f9',
    borderRadius: 8,
    border: '1px solid #f0f0f0',
  },
  sourcesList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
  },
  sourceTag: {
    cursor: 'pointer',
    fontSize: 12,
    margin: 0,
  },
  actions: {
    marginTop: 4,
    display: 'flex',
    gap: 4,
  },
  transferContainer: {
    marginTop: 8,
    padding: '10px 14px',
    background: '#e6f7ff',
    borderRadius: 8,
    border: '1px solid #91d5ff',
  },
  transferHeader: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: 6,
  },
  transferBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
  },
  inputContainer: {
    borderTop: '1px solid #f0f0f0',
    padding: '16px 24px',
    background: '#fafafa',
  },
  inputWrapper: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  input: {
    borderRadius: 12,
    fontSize: 14,
  },
  inputActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 8,
  },
};

export default AIChatPage;
