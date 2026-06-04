import { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Typography, Space, Tabs, Checkbox, message, Divider } from 'antd';
import {
  MobileOutlined, LockOutlined, MailOutlined, SafetyCertificateOutlined,
  RobotOutlined, WechatOutlined, QqOutlined,
} from '@ant-design/icons';
import { useAppDispatch } from '@/store/hooks';
import { loginByPhone, loginByEmail } from '@/store/slices/authSlice';
import { sendSmsCode } from '@/shared/api/auth';

const { Title, Text, Paragraph } = Typography;
type LoginMode = 'phone' | 'email';

const ClientLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [mode, setMode] = useState<LoginMode>('phone');
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [phoneValue, setPhoneValue] = useState('');

  const startCountdown = useCallback(() => {
    setCountdown(60);
    const timer = setInterval(() => {
      setCountdown((p) => { if (p <= 1) { clearInterval(timer); return 0; } return p - 1; });
    }, 1000);
  }, []);

  const handleSendCode = useCallback(async () => {
    if (!phoneValue || phoneValue.length !== 11) { message.warning('请输入正确的手机号'); return; }
    try {
      await sendSmsCode(phoneValue);
      message.success('验证码已发送');
      startCountdown();
    } catch (err: any) { message.error(err.message || '发送失败'); }
  }, [phoneValue, startCountdown]);

  const onPhoneLogin = async (values: { phone: string; code: string; remember?: boolean }) => {
    setLoading(true);
    try {
      await dispatch(loginByPhone({ ...values, remember: values.remember !== false })).unwrap();
      message.success('登录成功');
      navigate('/dashboard');
    } catch (err: any) { message.error(err); } finally { setLoading(false); }
  };

  const onEmailLogin = async (values: { email: string; password: string; remember?: boolean }) => {
    setLoading(true);
    try {
      await dispatch(loginByEmail({ ...values, remember: values.remember !== false })).unwrap();
      message.success('登录成功');
      navigate('/dashboard');
    } catch (err: any) { message.error(err); } finally { setLoading(false); }
  };

  return (
    <div style={styles.container}>
      <div style={styles.leftPanel}>
        <div style={styles.brandContent}>
          <div style={styles.logoBox}><RobotOutlined style={{ fontSize: 48, color: '#fff' }} /></div>
          <Title level={2} style={{ color: '#fff', margin: '24px 0 8px' }}>SmartDesk</Title>
          <Paragraph style={{ color: 'rgba(255,255,255,0.8)', fontSize: 16, maxWidth: 320 }}>
            AI 驱动的智能客服工单协同平台，让每一次对话都更高效。
          </Paragraph>
          <div style={styles.featureList}>
            {['🤖 AI 智能问答', '📋 工单自动流转', '💬 实时协作', '🔒 企业级安全'].map((f) => (
              <div key={f} style={styles.featureItem}>{f}</div>
            ))}
          </div>
        </div>
      </div>

      <div style={styles.rightPanel}>
        <div style={styles.formWrapper}>
          <div style={{ marginBottom: 32 }}>
            <Title level={3} style={{ margin: 0 }}>欢迎回来</Title>
            <Text type="secondary">登录您的 SmartDesk 账号</Text>
          </div>

          <Tabs activeKey={mode} onChange={(k) => setMode(k as LoginMode)} centered items={[
            {
              key: 'phone',
              label: <span><MobileOutlined /> 手机验证码</span>,
              children: (
                <Form onFinish={onPhoneLogin} size="large" autoComplete="off">
                  <Form.Item name="phone" rules={[{ required: true, message: '请输入手机号' }, { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确' }]}>
                    <Input prefix={<MobileOutlined style={{ color: '#bfbfbf' }} />} placeholder="请输入手机号" maxLength={11} value={phoneValue} onChange={(e) => setPhoneValue(e.target.value)} />
                  </Form.Item>
                  <Form.Item name="code" rules={[{ required: true, message: '请输入验证码' }, { len: 6, message: '验证码为6位数字' }]}>
                    <Input prefix={<SafetyCertificateOutlined style={{ color: '#bfbfbf' }} />} placeholder="请输入验证码" maxLength={6}
                      suffix={<Button type="link" size="small" disabled={countdown > 0} onClick={handleSendCode} style={{ padding: 0, fontSize: 13 }}>{countdown > 0 ? `${countdown}s 后重发` : '获取验证码'}</Button>}
                    />
                  </Form.Item>
                  <Form.Item>
                    <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 16 }}>
                      <Form.Item name="remember" valuePropName="checked" noStyle>
                        <Checkbox style={{ fontSize: 14 }}>记住我</Checkbox>
                      </Form.Item>
                    </div>
                    <Button type="primary" htmlType="submit" loading={loading} block style={styles.primaryBtn}>登 录</Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'email',
              label: <span><MailOutlined /> 邮箱密码</span>,
              children: (
                <Form onFinish={onEmailLogin} size="large" autoComplete="off">
                  <Form.Item name="email" rules={[{ required: true, message: '请输入邮箱' }, { pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: '邮箱格式不正确' }]}>
                    <Input prefix={<MailOutlined style={{ color: '#bfbfbf' }} />} placeholder="请输入邮箱" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少6位' }]}>
                    <Input.Password prefix={<LockOutlined style={{ color: '#bfbfbf' }} />} placeholder="请输入密码" />
                  </Form.Item>
                  <Form.Item>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                      <Form.Item name="remember" valuePropName="checked" noStyle>
                        <Checkbox style={{ fontSize: 14 }}>记住我</Checkbox>
                      </Form.Item>
                      <a style={{ fontSize: 14 }}>忘记密码？</a>
                    </div>
                    <Button type="primary" htmlType="submit" loading={loading} block style={styles.primaryBtn}>登 录</Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]} />

          <Divider plain><Text type="secondary" style={{ fontSize: 12 }}>其他登录方式</Text></Divider>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 24, marginBottom: 24 }}>
            <div style={styles.socialIcon}><WechatOutlined style={{ fontSize: 20, color: '#07c160' }} /></div>
            <div style={styles.socialIcon}><QqOutlined style={{ fontSize: 20, color: '#12b7f5' }} /></div>
            <div style={styles.socialIcon}><MailOutlined style={{ fontSize: 20, color: '#ea4335' }} /></div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <Space><Link to="/cs/login" style={styles.switchLink}>客服端</Link><Text type="secondary">|</Text><Link to="/admin/login" style={styles.switchLink}>管理端</Link></Space>
          </div>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { minHeight: '100vh', display: 'flex' },
  leftPanel: { flex: 1, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 },
  brandContent: { position: 'relative', zIndex: 1, textAlign: 'center' },
  logoBox: { width: 96, height: 96, borderRadius: 24, background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(10px)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto' },
  featureList: { marginTop: 32, display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center' },
  featureItem: { color: 'rgba(255,255,255,0.9)', fontSize: 15, padding: '8px 20px', background: 'rgba(255,255,255,0.1)', borderRadius: 8 },
  rightPanel: { width: 480, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff', padding: 40 },
  formWrapper: { width: '100%', maxWidth: 360 },
  primaryBtn: { height: 44, borderRadius: 8, fontWeight: 500 },
  socialIcon: { width: 40, height: 40, borderRadius: '50%', border: '1px solid #e8e8e8', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' },
  switchLink: { fontSize: 13, color: '#667eea' },
};

export default ClientLoginPage;
