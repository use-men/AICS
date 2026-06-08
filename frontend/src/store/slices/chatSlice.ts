import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

// ============================================================
//  Types
// ============================================================

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'agent';
  content: string;
  timestamp: number;
  status?: 'sending' | 'streaming' | 'done' | 'error';
  sources?: Array<{ question: string; answer: string; score: number }>;
  needHuman?: boolean;
  thinkingContent?: string;
  transferInfo?: {
    ticket_id: number;
    ticket_no: string;
    title: string;
    ticket_type: string;
    type_name: string;
    priority: string;
    service_id: number | null;
    service_name: string;
  };
}

/** 会话模式 */
export type ConversationMode = 'ai' | 'hybrid' | 'human';

interface ChatState {
  /** AI 问答消息列表 */
  messages: ChatMessage[];
  /** 后端会话 ID */
  conversationId: string;
  /** 当前会话模式 */
  mode: ConversationMode;
  /** 当前工单 ID（hybrid/human 模式） */
  ticketId: number | null;
}

// ============================================================
//  sessionStorage 持久化
// ============================================================

const STORAGE_KEY = 'smartdesk_ai_chat';

const WELCOME_MSG: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content:
    '你好！我是 SmartDesk AI 客服助手 👋\n\n我可以帮你解答以下问题：\n- 📋 工单相关问题\n- 🔐 账号与登录\n- 💰 退款与支付\n- ⚙️ 产品功能咨询\n\n请描述你的问题，我会尽力帮你解决！',
  timestamp: Date.now(),
  status: 'done',
};

function loadState(): ChatState {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed.messages) && parsed.messages.length > 0) {
        return {
          messages: parsed.messages,
          conversationId: parsed.conversationId || '',
          mode: parsed.mode || 'ai',
          ticketId: parsed.ticketId || null,
        };
      }
    }
  } catch {}
  return { messages: [WELCOME_MSG], conversationId: '', mode: 'ai', ticketId: null };
}

function saveState(state: ChatState) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      messages: state.messages,
      conversationId: state.conversationId,
      mode: state.mode,
      ticketId: state.ticketId,
    }));
  } catch {}
}

// ============================================================
//  初始状态（从 sessionStorage 恢复）
// ============================================================

const initialState: ChatState = loadState();

// ============================================================
//  Slice
// ============================================================

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    /** 追加一条消息 */
    addMessage(state, action: PayloadAction<ChatMessage>) {
      state.messages.push(action.payload);
      saveState(state);
    },

    /** 替换一条消息（用于流式更新 assistant 消息） */
    updateMessage(state, action: PayloadAction<ChatMessage>) {
      const idx = state.messages.findIndex((m) => m.id === action.payload.id);
      if (idx !== -1) {
        state.messages[idx] = action.payload;
      } else {
        // 如果消息不存在（可能是刷新后丢失），添加它
        state.messages.push(action.payload);
      }
      saveState(state);
    },

    /** 批量设置消息 */
    setMessages(state, action: PayloadAction<ChatMessage[]>) {
      state.messages = action.payload;
      saveState(state);
    },

    /** 设置会话 ID */
    setConversationId(state, action: PayloadAction<string>) {
      state.conversationId = action.payload;
      saveState(state);
    },

    /** 清空对话，重置为欢迎消息 */
    clearMessages(state) {
      state.messages = [
        {
          id: 'welcome',
          role: 'assistant',
          content: '对话已清空，有什么可以帮您？',
          timestamp: Date.now(),
          status: 'done',
        },
      ];
      state.conversationId = '';
      state.mode = 'ai';
      state.ticketId = null;
      saveState(state);
    },

    /** 设置会话模式 */
    setMode(state, action: PayloadAction<ConversationMode>) {
      state.mode = action.payload;
      saveState(state);
    },

    /** 设置工单 ID（进入 hybrid/human 模式） */
    setTicketId(state, action: PayloadAction<number | null>) {
      state.ticketId = action.payload;
      saveState(state);
    },

    /** 切换到 hybrid 模式 */
    switchToHybrid(state, action: PayloadAction<{ ticketId: number; ticketNo: string }>) {
      state.mode = 'hybrid';
      state.ticketId = action.payload.ticketId;
      saveState(state);
    },
  },
});

export const {
  addMessage,
  updateMessage,
  setMessages,
  setConversationId,
  clearMessages,
  setMode,
  setTicketId,
  switchToHybrid,
} = chatSlice.actions;
export default chatSlice.reducer;
