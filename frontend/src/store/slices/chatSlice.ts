import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

// ============================================================
//  Types
// ============================================================

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  status?: 'sending' | 'streaming' | 'done' | 'error';
  sources?: Array<{ question: string; answer: string; score: number }>;
  needHuman?: boolean;
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

interface ChatState {
  /** AI 问答消息列表 */
  messages: ChatMessage[];
  /** 后端会话 ID */
  conversationId: string;
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
        return parsed;
      }
    }
  } catch {}
  return { messages: [WELCOME_MSG], conversationId: '' };
}

function saveState(state: ChatState) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      messages: state.messages,
      conversationId: state.conversationId,
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
      saveState(state);
    },
  },
});

export const { addMessage, updateMessage, setMessages, setConversationId, clearMessages } =
  chatSlice.actions;
export default chatSlice.reducer;
