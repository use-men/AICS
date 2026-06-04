import { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { fetchCurrentUser } from '@/store/slices/authSlice';

/**
 * 路由守卫：
 * 1. 无 token → 跳转 /login
 * 2. 有 token 但无 user → 请求 /auth/me 获取用户信息
 * 3. 获取失败 → 清除 token，跳转 /login
 * 4. 已登录 → 放行
 */
const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const dispatch = useAppDispatch();
  const location = useLocation();
  const token = useAppSelector((s) => s.auth.token);
  const user = useAppSelector((s) => s.auth.user);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!token) {
      setChecking(false);
      return;
    }
    if (user) {
      setChecking(false);
      return;
    }
    // 有 token 但无 user → 拉取用户信息
    dispatch(fetchCurrentUser())
      .unwrap()
      .catch(() => { /* authSlice 会清除 token */ })
      .finally(() => setChecking(false));
  }, [token, user, dispatch]);

  // 加载中
  if (checking) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  // 无 token → 跳转登录页（根据当前路径判断跳哪个登录页）
  if (!token) {
    if (location.pathname.startsWith('/cs')) return <Navigate to="/cs/login" replace />;
    if (location.pathname.startsWith('/admin')) return <Navigate to="/admin/login" replace />;
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default AuthGuard;
