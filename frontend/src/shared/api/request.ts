import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';

// ============================================================
//  Axios 实例
// ============================================================

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

// ============================================================
//  Token 自动刷新 — 请求队列
// ============================================================

let isRefreshing = false;
let pendingQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: any) => void;
}> = [];

function processQueue(error: any, token: string | null = null) {
  pendingQueue.forEach(({ resolve, reject }) => {
    error ? reject(error) : resolve(token!);
  });
  pendingQueue = [];
}

function getStorage(): Storage {
  return localStorage.getItem('token_storage') === 'session' ? sessionStorage : localStorage;
}

async function tryRefreshToken(): Promise<string> {
  const storage = getStorage();
  const refreshToken = storage.getItem('refresh_token');
  if (!refreshToken) throw new Error('No refresh token');

  // 用原生 axios 避免循环拦截
  const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken });
  const { access_token, refresh_token: newRefresh } = data;

  storage.setItem('access_token', access_token);
  if (newRefresh) storage.setItem('refresh_token', newRefresh);

  return access_token;
}

// ============================================================
//  请求拦截器 — 自动附加 JWT
// ============================================================

request.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const pos = localStorage.getItem('token_storage');
  const token = pos === 'session'
    ? sessionStorage.getItem('access_token')
    : localStorage.getItem('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ============================================================
//  响应拦截器 — 401 自动刷新 + 统一错误处理
// ============================================================

request.interceptors.response.use(
  (res) => res.data,
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // ---- 401: 尝试刷新 Token ----
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // 排队等待刷新完成
        return new Promise<string>((resolve, reject) => {
          pendingQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return request(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const newToken = await tryRefreshToken();
        processQueue(null, newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return request(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        // 刷新失败 → 清除所有 token，跳转登录页
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('token_storage');
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // ---- 统一错误消息 ----
    const message = error.response?.data?.detail
      || error.response?.data?.message
      || `请求失败 (${error.response?.status || '网络错误'})`;
    return Promise.reject(new Error(message));
  },
);

export default request;
