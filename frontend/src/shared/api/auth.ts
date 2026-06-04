import request from './request';

// ============ Client ============

/** 发送手机验证码 */
export const sendSmsCode = (phone: string) =>
  request.post('/auth/send-code', { phone });

/** 手机验证码登录 */
export const loginByPhone = (phone: string, code: string) =>
  request.post('/auth/client/phone', { phone, code });

/** 邮箱密码登录 */
export const loginByEmail = (email: string, password: string) =>
  request.post('/auth/client/email', { email, password });

// ============ Customer Service ============

/** 客服端登录（工号+密码） */
export const loginByEmployeeId = (employee_id: string, password: string) =>
  request.post('/auth/cs/login', { employee_id, password });

// ============ Admin ============

/** 管理端登录 Step1（账号密码→发送验证码） */
export const adminLoginStep1 = (username: string, password: string) =>
  request.post('/auth/admin/login', { username, password });

/** 管理端登录 Step2（验证码→签发token） */
export const adminVerify = (username: string, code: string) =>
  request.post('/auth/admin/verify', { username, code });

// ============ Common ============

/** 获取当前用户信息 */
export const getUserInfo = () =>
  request.get('/auth/me');

/** 刷新 Token */
export const refreshToken = (refresh_token: string) =>
  request.post('/auth/refresh', { refresh_token });

/** 退出登录 */
export const logout = () =>
  request.post('/auth/logout');
