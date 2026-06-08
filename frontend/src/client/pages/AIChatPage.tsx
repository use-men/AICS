/**
 * AIChatPage — ChatGPT 风格 AI 客服聊天界面（微信风格气泡）
 *
 * 支持：
 * - AI 智能客服对话
 * - 转人工后 WebSocket 实时聊天（直接嵌入 ChatWindow）
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Button, Input, Typography, Spin, message as antMsg, Tag, Tooltip, Switch } from 'antd';
import {
  SendOutlined, RobotOutlined, UserOutlined, CustomerServiceOutlined,
  ClearOutlined, CopyOutlined, FileTextOutlined, BulbOutlined,
} from '@ant-design/icons';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { addMessage, updateMessage, clearMessages, setConversationId, switchToHybrid, setMessages, setMode, setTicketId } from '@/store/slices/chatSlice';
import type { ChatMessage } from '@/store/slices/chatSlice';
import ChatWindow from '@/shared/components/ChatWindow';
import { useTheme } from '@/locales/theme';

const { Text } = Typography;

const AIChatPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const messages = useAppSelector((s) => s.chat.messages);
  const conversationId = useAppSelector((s) => s.chat.conversationId);
  const mode = useAppSelector((s) => s.chat.mode);
  const ticketId = useAppSelector((s) => s.chat.ticketId);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [deepThinking, setDeepThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);
  const { mode: themeMode } = useTheme();
  const isDark = themeMode === 'dark';

  // 获取当前转人工信息
  const transferMsg = messages.find((m) => m.transferInfo);
  const transferInfo = transferMsg?.transferInfo;

  // hybrid 模式下使用 ticketId
  const currentTicketId = ticketId || transferInfo?.ticket_id;

  useEffect(() => {
    if (!conversationId) dispatch(setConversationId(`chat_${user?.id || 'guest'}_${Date.now()}`));
  }, [conversationId, dispatch, user?.id]);

  // Hybrid 模式下，验证工单是否有效
  useEffect(() => {
    if (mode === 'hybrid' && currentTicketId) {
      const validateTicket = async () => {
        try {
          const token = localStorage.getItem('access_token');
          const res = await fetch(`/api/v1/tickets/${currentTicketId}`, {
            headers: { 'Authorization': `Bearer ${token}` },
          });
          if (!res.ok) {
            // 工单不存在或已关闭，重置为 AI 模式
            dispatch(setMode('ai'));
            dispatch(setTicketId(null));
          }
        } catch (e) {
          console.log('[HybridMode] 验证工单失败:', e);
        }
      };
      validateTicket();
    }
  }, [mode, currentTicketId]);

  // Hybrid 模式下，从后端加载工单消息历史
  useEffect(() => {
    if (mode === 'hybrid' && currentTicketId && messages.length <= 2) {
      const loadHistory = async () => {
        try {
          const res = await fetch(`/api/v1/conversation/messages/${currentTicketId}`);
          if (res.ok) {
            const history = await res.json();
            if (history.length > 0) {
              // 将后端消息转换为 ChatMessage 格式
              const backendMsgs: ChatMessage[] = history.map((m: any) => ({
                id: `backend_${m.id}`,
                role: m.sender_type === 'ai' ? 'assistant' : m.sender_type === 'user' ? 'user' : 'agent' as const,
                content: m.content,
                timestamp: new Date(m.created_at).getTime(),
                status: 'done' as const,
              }));
              // 合并消息（避免重复）
              const existingIds = new Set(messages.map(m => m.id));
              const newMsgs = backendMsgs.filter(m => !existingIds.has(m.id));
              if (newMsgs.length > 0) {
                dispatch(setMessages([...messages, ...newMsgs]));
              }
            }
          }
        } catch (e) {
          console.log('[HybridMode] 加载历史消息失败:', e);
        }
      };
      loadHistory();
    }
  }, [mode, currentTicketId]);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => { inputRef.current?.focus(); }, [loading]);

  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || loading) return;
    const convId = conversationId || `chat_${user?.id || 'guest'}_${Date.now()}`;
    if (!conversationId) dispatch(setConversationId(convId));

    const userMsg: ChatMessage = { id: `user_${Date.now()}`, role: 'user', content: text, timestamp: Date.now(), status: 'done' };
    const assistantMsg: ChatMessage = { id: `assistant_${Date.now()}`, role: 'assistant', content: '', timestamp: Date.now(), status: 'streaming' };
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
          deep_thinking: deepThinking,
          ticket_id: currentTicketId, // hybrid 模式下传入 ticket_id
        }),
      });
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = '', thinkingContent = '';
      let sources: Array<{ question: string; answer: string; score: number }> = [];
      let needHuman = false;
      let transferInfo: ChatMessage['transferInfo'] = undefined;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          for (const line of chunk.split('\n')) {
            if (!line.startsWith('data: ')) continue;
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            try {
              const p = JSON.parse(data);
              if (p.type === 'thinking' && p.content) { thinkingContent += p.content; dispatch(updateMessage({ ...assistantMsg, thinkingContent, content: fullContent, status: 'streaming' })); }
              if (p.type === 'delta' && p.content) { fullContent += p.content; dispatch(updateMessage({ ...assistantMsg, thinkingContent, content: fullContent, status: 'streaming' })); }
              if (p.type === 'sources') sources = p.sources || [];
              if (p.type === 'done') { needHuman = p.need_human || false; sources = p.sources || sources; if (p.content) fullContent = p.content; console.log('[SSE] done event:', p); }
              if (p.type === 'transfer') { transferInfo = { ticket_id: p.ticket_id, ticket_no: p.ticket_no, title: p.title, ticket_type: p.ticket_type, type_name: p.type_name, priority: p.priority, service_id: p.service_id, service_name: p.service_name }; console.log('[SSE] transfer event:', transferInfo); }
            } catch {}
          }
        }
      }
      if (!fullContent) {
        const fb = await fetch('/api/v1/agent/cs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, conversation_id: convId, user_id: user?.id }) });
        const r = await fb.json(); fullContent = r.answer || '抱歉，暂时无法回答'; sources = r.sources || []; needHuman = r.need_human || false;
      }

      // 调试日志
      console.log('[handleSend] needHuman:', needHuman, 'transferInfo:', transferInfo);

      dispatch(updateMessage({ ...assistantMsg, content: fullContent, thinkingContent: thinkingContent || undefined, sources, needHuman, transferInfo, status: 'done' }));
      if (needHuman && transferInfo) {
        dispatch(addMessage({ id: `sys_${Date.now()}`, role: 'system', content: `🔄 已自动创建工单 ${transferInfo.ticket_no}，正在转接人工客服（${transferInfo.service_name || '排队中'}），请稍候...\n\n💡 您仍然可以继续向 AI 提问`, timestamp: Date.now(), status: 'done' }));
        // 切换到 hybrid 模式
        dispatch(switchToHybrid({ ticketId: transferInfo.ticket_id, ticketNo: transferInfo.ticket_no }));
      }
    } catch { dispatch(updateMessage({ ...assistantMsg, content: '抱歉，AI客服暂时不可用，请稍后再试。', status: 'error' })); }
    finally { setLoading(false); }
  }, [inputValue, loading, user?.id, conversationId, dispatch, deepThinking]);

  const handleTransferHuman = async () => {
    const um = messages.filter((m) => m.role === 'user').map((m) => m.content).join('\n');
    if (!um) return;
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/v1/agent/create-ticket', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, body: JSON.stringify({ content: um, conversation_id: conversationId, user_id: user?.id }) });
      const r = await res.json();
      if (r.ticket_id) {
        let si = '';
        try { const dr = await fetch('/api/v1/dispatch/auto', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, body: JSON.stringify({ ticket_id: r.ticket_id, ticket_type: r.ticket_type || 'after_sales' }) }); const dd = await dr.json(); if (dd.service_name) si = `\n已分配给客服: ${dd.service_name}`; } catch {}
        dispatch(addMessage({ id: `sys_${Date.now()}`, role: 'system', content: `✅ 工单已创建: ${r.ticket_id}（${r.ticket_type}）${si}\n\n💡 您仍然可以继续向 AI 提问`, timestamp: Date.now(), status: 'done' }));
        // 切换到 hybrid 模式
        dispatch(switchToHybrid({ ticketId: r.ticket_id, ticketNo: r.ticket_id.toString() }));
        antMsg.success('工单已创建，进入协同模式');
      }
    } catch { antMsg.error('转人工失败，请稍后再试'); }
  };

  const handleClear = () => { dispatch(clearMessages()); dispatch(setConversationId(`chat_${user?.id || 'guest'}_${Date.now()}`)); };
  const handleCopy = (c: string) => { navigator.clipboard.writeText(c); antMsg.success('已复制'); };

  const renderContent = (content: string) => content.split('\n').map((line, i) => {
    line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    line = line.replace(/`(.*?)`/g, '<code style="background:rgba(0,0,0,0.06);padding:2px 6px;border-radius:4px">$1</code>');
    return <div key={i} style={{ margin: i === 0 ? 0 : '4px 0', fontSize: 14, lineHeight: 1.6 }} dangerouslySetInnerHTML={{ __html: line || '&nbsp;' }} />;
  });

  // 暗色模式颜色
  const darkColors = {
    bg: isDark ? '#1a1a1a' : '#f5f5f5',
    cardBg: isDark ? '#2a2a2a' : '#fff',
    border: isDark ? '#404040' : '#e8e8e8',
    text: isDark ? '#e8e8e8' : '#333',
    textSecondary: isDark ? '#999' : '#666',
    aiBubble: isDark ? '#2a2a2a' : '#fff',
    userBubble: '#667eea',
    systemBg: isDark ? '#1a2a1a' : '#f6ffed',
    systemBorder: isDark ? '#2d4a2d' : '#b7eb8f',
    transferBg: isDark ? '#1a2a3a' : '#e6f7ff',
    transferBorder: isDark ? '#2a4a6a' : '#91d5ff',
  };

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 160px)', background: darkColors.bg, borderRadius: 12, overflow: 'hidden' }}>
      {/* 左侧：AI 对话区域 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: mode === 'hybrid' && currentTicketId ? `1px solid ${darkColors.border}` : 'none', overflow: 'hidden' }}>
        {/* AI 模式标识 */}
        {mode === 'hybrid' && (
          <div style={{ padding: '8px 16px', background: darkColors.transferBg, borderBottom: `1px solid ${darkColors.transferBorder}`, display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
            <RobotOutlined style={{ color: '#1890ff' }} />
            <Text strong style={{ fontSize: 13, color: '#1890ff' }}>🤖 SmartDesk AI</Text>
            <Text style={{ fontSize: 12, color: darkColors.textSecondary }}>· 协同模式</Text>
          </div>
        )}

        {/* 消息区域 */}
        <div style={{ flex: 1, overflow: 'auto', padding: '16px 0', minHeight: 0 }}>
          {messages.map((msg) => {
            const isUser = msg.role === 'user';
            const isSystem = msg.role === 'system';
            const isAgent = msg.role === 'agent';
            return (
              <div key={msg.id} style={{ display: 'flex', flexDirection: isUser ? 'row-reverse' : 'row', alignItems: 'flex-start', gap: 10, padding: '6px 20px' }}>
                {/* 头像 */}
                <div style={{ flexShrink: 0, marginTop: 2 }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: 18, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: isUser ? '#667eea' : isSystem ? '#52c41a' : isAgent ? '#52c41a' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  }}>
                    {isUser ? <UserOutlined style={{ color: '#fff', fontSize: 14 }} /> : isSystem ? <FileTextOutlined style={{ color: '#fff', fontSize: 14 }} /> : isAgent ? <CustomerServiceOutlined style={{ color: '#fff', fontSize: 14 }} /> : <RobotOutlined style={{ color: '#fff', fontSize: 14 }} />}
                  </div>
                </div>
                {/* 消息区域 */}
                <div style={{ maxWidth: '70%', display: 'flex', flexDirection: 'column' }}>
                  {!isUser && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                      <Text strong style={{ fontSize: 12, color: darkColors.textSecondary }}>{isSystem ? '系统' : isAgent ? '客服' : 'SmartDesk AI'}</Text>
                      <Text style={{ fontSize: 11, color: darkColors.textSecondary }}>{new Date(msg.timestamp).toLocaleTimeString('zh-CN')}</Text>
                    </div>
                  )}
                  {msg.thinkingContent && (
                    <div style={{ marginBottom: 6, padding: '8px 12px', background: isDark ? '#2a1a3a' : '#f9f0ff', borderRadius: 8, border: `1px solid ${isDark ? '#4a2a6a' : '#efdbff'}` }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}><BulbOutlined style={{ color: '#722ed1', marginRight: 4 }} /><Text style={{ fontSize: 12, color: '#722ed1', fontWeight: 500 }}>深度思考</Text></div>
                      <div style={{ maxHeight: 200, overflow: 'auto' }}>{msg.thinkingContent.split('\n').map((l, i) => <div key={i} style={{ fontSize: 12, color: darkColors.textSecondary, lineHeight: 1.5, margin: '2px 0' }}>{l || ' '}</div>)}</div>
                    </div>
                  )}
                  <div style={{
                    background: isUser ? '#667eea' : isSystem ? darkColors.systemBg : isAgent ? darkColors.systemBg : darkColors.aiBubble,
                    color: isUser ? '#fff' : darkColors.text,
                    padding: '10px 14px',
                    borderRadius: isUser ? '16px 16px 4px 16px' : isSystem ? '8px' : isAgent ? '16px 16px 16px 4px' : '16px 16px 16px 4px',
                    fontSize: 14, lineHeight: 1.6, wordBreak: 'break-word',
                    boxShadow: !isUser ? (isDark ? '0 1px 2px rgba(0,0,0,0.3)' : '0 1px 2px rgba(0,0,0,0.06)') : 'none',
                    border: isSystem || isAgent ? `1px solid ${darkColors.systemBorder}` : 'none',
                  }}>
                    {isUser && <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.6)', marginBottom: 2 }}>{new Date(msg.timestamp).toLocaleTimeString('zh-CN')}</div>}
                    {msg.status === 'streaming' && !msg.content && !msg.thinkingContent ? <Spin size="small" /> : renderContent(msg.content)}
                    {msg.status === 'streaming' && msg.content && <span style={{ animation: 'blink 1s infinite', color: isUser ? '#fff' : '#667eea' }}>▊</span>}
                  </div>
                  {msg.sources && msg.sources.length > 0 && msg.status === 'done' && (
                    <div style={{ marginTop: 6, padding: '6px 10px', background: darkColors.cardBg, borderRadius: 8, border: `1px solid ${darkColors.border}` }}>
                      <Text style={{ fontSize: 12, display: 'block', marginBottom: 4, color: darkColors.textSecondary }}>📚 参考来源:</Text>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>{msg.sources.slice(0, 3).map((s, i) => <Tooltip key={i} title={s.answer}><Tag style={{ cursor: 'pointer', fontSize: 12 }}>{i + 1}. {s.question.slice(0, 20)}... <Text style={{ fontSize: 10, color: darkColors.textSecondary }}>{(s.score * 100).toFixed(0)}%</Text></Tag></Tooltip>)}</div>
                    </div>
                  )}
                  {msg.transferInfo && (
                    <div style={{ marginTop: 6, padding: '10px 14px', background: darkColors.transferBg, borderRadius: 8, border: `1px solid ${darkColors.transferBorder}` }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}><CustomerServiceOutlined style={{ color: '#1890ff', marginRight: 6 }} /><Text strong style={{ fontSize: 13, color: '#1890ff' }}>已进入协同模式</Text></div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                        <div><Text style={{ fontSize: 12, color: darkColors.textSecondary }}>工单号: </Text><Text style={{ fontSize: 12, color: darkColors.text }}>{msg.transferInfo.ticket_no}</Text></div>
                        <div><Text style={{ fontSize: 12, color: darkColors.textSecondary }}>类型: </Text><Text style={{ fontSize: 12, color: darkColors.text }}>{msg.transferInfo.type_name}</Text></div>
                        <div><Text style={{ fontSize: 12, color: darkColors.textSecondary }}>优先级: </Text><Tag color={msg.transferInfo.priority === 'urgent' ? 'red' : msg.transferInfo.priority === 'high' ? 'orange' : 'blue'} style={{ fontSize: 11 }}>{msg.transferInfo.priority}</Tag></div>
                        {msg.transferInfo.service_name && <div><Text style={{ fontSize: 12, color: darkColors.textSecondary }}>分配客服: </Text><Text strong style={{ fontSize: 12, color: darkColors.text }}>{msg.transferInfo.service_name}</Text></div>}
                      </div>
                    </div>
                  )}
                  {!isUser && msg.status === 'done' && msg.content && (
                    <div style={{ marginTop: 4 }}><Tooltip title="复制"><Button type="text" size="small" icon={<CopyOutlined />} onClick={() => handleCopy(msg.content)} style={{ fontSize: 12, color: darkColors.textSecondary }} /></Tooltip></div>
                  )}
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* AI 输入区域 */}
        <div style={{ borderTop: `1px solid ${darkColors.border}`, padding: '12px 20px', background: darkColors.cardBg, flexShrink: 0 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <Input.TextArea ref={inputRef} value={inputValue} onChange={(e) => setInputValue(e.target.value)}
              onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder={mode === 'hybrid' ? "继续向 AI 提问... (Enter 发送)" : "输入你的问题... (Enter 发送, Shift+Enter 换行)"}
              autoSize={{ minRows: 1, maxRows: 4 }}
              style={{ flex: 1, borderRadius: 20, fontSize: 14, resize: 'none', background: isDark ? '#1a1a1a' : '#fff', color: darkColors.text }}
              disabled={loading}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
              <Tooltip title={deepThinking ? '深度思考已开启' : '开启深度思考'}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <BulbOutlined style={{ color: deepThinking ? '#722ed1' : darkColors.textSecondary, fontSize: 14 }} />
                  <Switch size="small" checked={deepThinking} onChange={setDeepThinking} disabled={loading} />
                </div>
              </Tooltip>
              <Button icon={<ClearOutlined />} onClick={handleClear} size="small" disabled={loading}>清空</Button>
              {mode === 'ai' && (
                <Button icon={<CustomerServiceOutlined />} onClick={handleTransferHuman} size="small" disabled={loading}>
                  转人工
                </Button>
              )}
              <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading} size="small" style={{ borderRadius: 20 }}>发送</Button>
            </div>
          </div>
          <div style={{ textAlign: 'center', marginTop: 6 }}>
            <Text style={{ fontSize: 11, color: darkColors.textSecondary }}>
              {mode === 'hybrid' ? '协同模式 · AI + 人工客服' : 'SmartDesk AI 客服 · 基于知识库的智能问答'}
            </Text>
          </div>
        </div>
      </div>

      {/* 右侧：人工客服实时聊天（仅 hybrid 模式显示） */}
      {mode === 'hybrid' && currentTicketId && (
        <div style={{ width: 450, display: 'flex', flexDirection: 'column', background: darkColors.cardBg, overflow: 'hidden' }}>
          {/* 客服聊天标识 */}
          <div style={{ padding: '8px 16px', background: darkColors.systemBg, borderBottom: `1px solid ${darkColors.systemBorder}`, display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
            <CustomerServiceOutlined style={{ color: '#52c41a' }} />
            <Text strong style={{ fontSize: 13, color: '#52c41a' }}>👨 客服</Text>
            <Text style={{ fontSize: 12, color: darkColors.textSecondary }}>· 人工服务</Text>
          </div>

          {/* ChatWindow 组件 */}
          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
            <ChatWindow
              ticketId={currentTicketId}
              userId={user?.id || 0}
              userType="user"
              ticketTitle={transferInfo?.ticket_no || `工单 #${currentTicketId}`}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default AIChatPage;
