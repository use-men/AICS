import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import * as authAPI from '@/shared/api/auth';

// ============================================================
//  Types
// ============================================================

export interface UserInfo {
  id: number;
  username: string;
  email: string;
  phone?: string;
  nickname?: string;
  avatar?: string;
  roles: string[];
  permissions: string[];
  employee_id?: string;
}

/** 三种登录端 */
export type LoginType = 'client' | 'cs' | 'admin';

interface AuthState {
  user: UserInfo | null;
  token: string | null;
  refreshToken: string | null;
  loginType: LoginType | null;
  loading: boolean;
  error: string | null;
}

// ============================================================
//  Token 存储工具 — 支持 localStorage / sessionStorage
// ============================================================

/** "记住我" 时用 localStorage（关浏览器也保留），否则用 sessionStorage */
function saveTokens(access: string, refresh: string, remember: boolean) {
  const storage = remember ? localStorage : sessionStorage;
  // 先清除另一处的旧数据
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  sessionStorage.removeItem('access_token');
  sessionStorage.removeItem('refresh_token');
  // 写入目标存储
  storage.setItem('access_token', access);
  storage.setItem('refresh_token', refresh);
  // 标记存储位置
  localStorage.setItem('token_storage', remember ? 'local' : 'session');
}

function loadToken(key: string): string | null {
  // 优先从标记的存储位置读取
  const pos = localStorage.getItem('token_storage');
  if (pos === 'session') return sessionStorage.getItem(key);
  return localStorage.getItem(key);
}

function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('login_type');
  localStorage.removeItem('token_storage');
  sessionStorage.removeItem('access_token');
  sessionStorage.removeItem('refresh_token');
}

// ============================================================
//  初始状态 — 从存储恢复
// ============================================================

const initialState: AuthState = {
  user: null,
  token: loadToken('access_token'),
  refreshToken: loadToken('refresh_token'),
  loginType: (localStorage.getItem('login_type') as LoginType) || null,
  loading: false,
  error: null,
};

// ============================================================
//  Async Thunks
// ============================================================

/** 用户端 — 手机验证码登录 */
export const loginByPhone = createAsyncThunk(
  'auth/loginByPhone',
  async (payload: { phone: string; code: string; remember?: boolean }, { rejectWithValue }) => {
    try {
      const res: any = await authAPI.loginByPhone(payload.phone, payload.code);
      saveTokens(res.access_token, res.refresh_token, payload.remember !== false);
      localStorage.setItem('login_type', 'client');
      const me: any = await authAPI.getUserInfo();
      return { token: res.access_token, user: me, loginType: 'client' as LoginType };
    } catch (err: any) {
      return rejectWithValue(err.message || '登录失败');
    }
  },
);

/** 用户端 — 邮箱密码登录 */
export const loginByEmail = createAsyncThunk(
  'auth/loginByEmail',
  async (payload: { email: string; password: string; remember?: boolean }, { rejectWithValue }) => {
    try {
      const res: any = await authAPI.loginByEmail(payload.email, payload.password);
      saveTokens(res.access_token, res.refresh_token, payload.remember !== false);
      localStorage.setItem('login_type', 'client');
      const me: any = await authAPI.getUserInfo();
      return { token: res.access_token, user: me, loginType: 'client' as LoginType };
    } catch (err: any) {
      return rejectWithValue(err.message || '登录失败');
    }
  },
);

/** 客服端 — 工号密码登录 */
export const loginByCS = createAsyncThunk(
  'auth/loginByCS',
  async (payload: { employee_id: string; password: string; remember?: boolean }, { rejectWithValue }) => {
    try {
      const res: any = await authAPI.loginByEmployeeId(payload.employee_id, payload.password);
      saveTokens(res.access_token, res.refresh_token, payload.remember !== false);
      localStorage.setItem('login_type', 'cs');
      const me: any = await authAPI.getUserInfo();
      return { token: res.access_token, user: me, loginType: 'cs' as LoginType };
    } catch (err: any) {
      return rejectWithValue(err.message || '登录失败');
    }
  },
);

/** 管理端 — 邮箱验证码验证（Step2） */
export const loginByAdmin = createAsyncThunk(
  'auth/loginByAdmin',
  async (payload: { username: string; code: string; remember?: boolean }, { rejectWithValue }) => {
    try {
      const res: any = await authAPI.adminVerify(payload.username, payload.code);
      saveTokens(res.access_token, res.refresh_token, payload.remember !== false);
      localStorage.setItem('login_type', 'admin');
      const me: any = await authAPI.getUserInfo();
      return { token: res.access_token, user: me, loginType: 'admin' as LoginType };
    } catch (err: any) {
      return rejectWithValue(err.message || '验证失败');
    }
  },
);

/** 获取当前用户信息（页面刷新时调用） */
export const fetchCurrentUser = createAsyncThunk(
  'auth/fetchCurrentUser',
  async (_, { rejectWithValue }) => {
    try {
      const me: any = await authAPI.getUserInfo();
      return me;
    } catch (err: any) {
      return rejectWithValue(err.message || '获取用户信息失败');
    }
  },
);

/** 退出登录 */
export const logoutThunk = createAsyncThunk(
  'auth/logout',
  async (_, { dispatch }) => {
    try { await authAPI.logout(); } catch { /* ignore */ }
    dispatch(logoutAction());
  },
);

// ============================================================
//  Slice
// ============================================================

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logoutAction(state) {
      state.user = null;
      state.token = null;
      state.refreshToken = null;
      state.loginType = null;
      state.error = null;
      clearTokens();
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // ---- 所有登录 thunks 共用 pending/fulfilled/rejected ----
    const pending = (state: AuthState) => { state.loading = true; state.error = null; };
    const rejected = (state: AuthState, action: any) => { state.loading = false; state.error = action.payload; };

    builder
      // loginByPhone
      .addCase(loginByPhone.pending, pending)
      .addCase(loginByPhone.fulfilled, (state, action) => {
        state.loading = false;
        state.token = action.payload.token;
        state.user = action.payload.user;
        state.loginType = action.payload.loginType;
      })
      .addCase(loginByPhone.rejected, rejected)

      // loginByEmail
      .addCase(loginByEmail.pending, pending)
      .addCase(loginByEmail.fulfilled, (state, action) => {
        state.loading = false;
        state.token = action.payload.token;
        state.user = action.payload.user;
        state.loginType = action.payload.loginType;
      })
      .addCase(loginByEmail.rejected, rejected)

      // loginByCS
      .addCase(loginByCS.pending, pending)
      .addCase(loginByCS.fulfilled, (state, action) => {
        state.loading = false;
        state.token = action.payload.token;
        state.user = action.payload.user;
        state.loginType = action.payload.loginType;
      })
      .addCase(loginByCS.rejected, rejected)

      // loginByAdmin
      .addCase(loginByAdmin.pending, pending)
      .addCase(loginByAdmin.fulfilled, (state, action) => {
        state.loading = false;
        state.token = action.payload.token;
        state.user = action.payload.user;
        state.loginType = action.payload.loginType;
      })
      .addCase(loginByAdmin.rejected, rejected)

      // fetchCurrentUser
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.user = action.payload;
      })
      .addCase(fetchCurrentUser.rejected, (state) => {
        state.user = null;
        state.token = null;
        clearTokens();
      })

      // logoutThunk
      .addCase(logoutThunk.fulfilled, (state) => {
        state.user = null;
        state.token = null;
        state.refreshToken = null;
        state.loginType = null;
      });
  },
});

export const { logoutAction, clearError } = authSlice.actions;
export default authSlice.reducer;
