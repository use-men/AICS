/**
 * useChat — WebSocket 实时聊天 Hook
 *
 * 功能:
 * - 连接管理（自动重连）
 * - 消息收发
 * - 在线状态
 * - 未读消息
 * - 已读状态
 */

import { useState, useEffect, useRef, useCallback } from 'react';

// ---- 类型定义 ----

export interface ChatMessage {
  id: number;
  ticket_id: number;
  sender_id: number;
  sender_type: 'user' | 'service' | 'admin' | 'ai';
  content: string;
  message_type: 'text' | 'image' | 'file';
  is_read: boolean;
  created_at: string;
}

export interface UseChatOptions {
  ticketId: number;
  userId: number;
  userType: 'user' | 'service';
  onNewMessage?: (message: ChatMessage) => void;
  onNewTicket?: (ticketId: number) => void;
  onTicketStatusChanged?: (ticketId: number, status: string) => void;
  onUserJoined?: (senderType: string, senderId: number) => void;
  onUserLeft?: (senderType: string, senderId: number) => void;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  connected: boolean;
  onlineCount: number;
  unreadCount: number;
  sendMessage: (content: string, messageType?: string) => void;
  markRead: () => void;
  loadHistory: () => Promise<void>;
  connect: () => void;
  disconnect: () => void;
}

// ---- Hook ----

export function useChat(options: UseChatOptions): UseChatReturn {
  const {
    ticketId,
    userId,
    userType,
    onNewMessage,
    onNewTicket,
    onTicketStatusChanged,
    onUserJoined,
    onUserLeft,
  } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const [onlineCount, setOnlineCount] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<any>(null);
  const mountedRef = useRef(true);
  const wsIdRef = useRef(0); // 追踪当前活跃的 WebSocket ID

  // 用 ref 存 callbacks 和 loadHistory，避免重渲染触发 reconnect
  const onNewMessageRef = useRef(onNewMessage);
  const onNewTicketRef = useRef(onNewTicket);
  const onTicketStatusChangedRef = useRef(onTicketStatusChanged);
  const onUserJoinedRef = useRef(onUserJoined);
  const onUserLeftRef = useRef(onUserLeft);
  const loadHistoryRef = useRef<() => Promise<void>>(() => Promise.resolve());

  useEffect(() => { onNewMessageRef.current = onNewMessage; }, [onNewMessage]);
  useEffect(() => { onNewTicketRef.current = onNewTicket; }, [onNewTicket]);
  useEffect(() => { onTicketStatusChangedRef.current = onTicketStatusChanged; }, [onTicketStatusChanged]);
  useEffect(() => { onUserJoinedRef.current = onUserJoined; }, [onUserJoined]);
  useEffect(() => { onUserLeftRef.current = onUserLeft; }, [onUserLeft]);

  // ---- WebSocket URL ----

  // 同源连接（前端和后端都在同一端口）
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsBase = `${wsProtocol}//${window.location.host}`;

  const wsUrl = userType === 'user'
    ? `${wsBase}/api/v1/ws/chat/user/${userId}`
    : `${wsBase}/api/v1/ws/chat/service/${userId}`;

  // ---- 加载历史消息 ----

  const loadHistory = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
      const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

      const res = await fetch(`/api/v1/chat/messages/${ticketId}?limit=50`, { headers });
      const data = await res.json();
      if (mountedRef.current) {
        setMessages(data.messages || []);
      }

      const unreadRes = await fetch(`/api/v1/chat/unread/${ticketId}?reader_type=${userType}`, { headers });
      const unreadData = await unreadRes.json();
      if (mountedRef.current) {
        setUnreadCount(unreadData.unread_count || 0);
      }
    } catch (error) {
      console.error('[Chat] 加载历史消息失败:', error);
    }
  }, [ticketId, userType]);

  // 同步 ref
  useEffect(() => { loadHistoryRef.current = loadHistory; }, [loadHistory]);

  // connect ref — 让 onclose 调用最新的 connect
  const connectRef = useRef<() => void>(() => {});

  // ---- 连接（仅依赖 wsUrl 和 ticketId，不依赖 callbacks） ----

  const connect = useCallback(() => {
    const state = wsRef.current?.readyState;
    if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) return;

    // 清理旧连接
    if (wsRef.current) {
      try { wsRef.current.close(); } catch {}
      wsRef.current = null;
    }

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    const myId = ++wsIdRef.current; // 标记当前 WebSocket

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnected(true);
      console.log('[Chat] WebSocket 已连接');

      // 延迟进入房间，确保连接完全稳定
      setTimeout(() => {
        if (ws.readyState === WebSocket.OPEN && mountedRef.current) {
          ws.send(JSON.stringify({
            type: 'join_room',
            ticket_id: ticketId,
          }));
        }
      }, 200);
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(event.data);

        switch (msg.type) {
          case 'new_message': {
            const newMsg = msg.message as ChatMessage;
            setMessages((prev) => [...prev, newMsg]);
            if (newMsg.sender_type !== userType) {
              setUnreadCount((prev) => prev + 1);
            }
            onNewMessageRef.current?.(newMsg);
            break;
          }

          case 'user_joined':
            setOnlineCount(msg.online_count);
            onUserJoinedRef.current?.(msg.sender_type, msg.sender_id);
            break;

          case 'user_left':
            setOnlineCount(msg.online_count);
            onUserLeftRef.current?.(msg.sender_type, msg.sender_id);
            break;

          case 'messages_read':
            setMessages((prev) =>
              prev.map((m) => ({ ...m, is_read: true })),
            );
            break;

          case 'ticket_status_changed':
            onTicketStatusChangedRef.current?.(msg.ticket_id, msg.status);
            break;

          case 'new_ticket_alert':
            onNewTicketRef.current?.(msg.data?.ticket_id);
            break;

          case 'pong':
            break;
        }
      } catch (e) {
        console.error('[Chat] onmessage 解析错误:', e);
      }
    };

    ws.onclose = (event) => {
      console.log('[Chat] onclose:', { myId, wsId: wsIdRef.current, mounted: mountedRef.current, code: event.code, reason: event.reason });
      // 只有当前活跃的 WebSocket 才触发重连
      if (!mountedRef.current || myId !== wsIdRef.current) return;
      setConnected(false);
      console.log('[Chat] 连接断开，3秒后重连...');
      reconnectTimer.current = setTimeout(() => connectRef.current(), 3000);
    };

    ws.onerror = (error) => {
      console.error('[Chat] WebSocket 错误:', error);
    };

    // 同步 connectRef，确保 onclose 调用最新版本
    connectRef.current = connect;
  }, [wsUrl, ticketId, userType]); // 用 ref 调用 loadHistory，不放入依赖

  // ---- 断开 ----

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'leave_room',
          ticket_id: ticketId,
        }));
      }
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, [ticketId]);

  // ---- 发送消息 ----

  const sendMessage = useCallback((content: string, messageType: string = 'text') => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({
      type: 'send_message',
      ticket_id: ticketId,
      content,
      message_type: messageType,
    }));
  }, [ticketId]);

  // ---- 标记已读 ----

  const markRead = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({
      type: 'mark_read',
      ticket_id: ticketId,
    }));
    setUnreadCount(0);
  }, [ticketId]);

  // ---- 心跳 ----

  useEffect(() => {
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // ---- 连接成功后加载历史消息 ----

  useEffect(() => {
    if (connected) {
      loadHistoryRef.current();
    }
  }, [connected]);

  // ---- 自动连接/断开 ----

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    messages,
    connected,
    onlineCount,
    unreadCount,
    sendMessage,
    markRead,
    loadHistory,
    connect,
    disconnect,
  };
}
