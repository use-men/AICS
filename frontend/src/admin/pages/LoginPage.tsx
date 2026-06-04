import { useState, useRef, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Typography, Steps, Space, message, Divider } from 'antd';
import { UserOutlined, LockOutlined, SafetyOutlined, MailOutlined, CheckCircleFilled, KeyOutlined } from '@ant-design/icons';
import { useAppDispatch } from '@/store/hooks';
import { loginByAdmin } from '@/store/slices/authSlice';
import { adminLoginStep1 } from '@/shared/api/auth';

const { Title, Text, Paragraph } = Typography;

const AdminLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [adminUser, setAdminUser] = useState('');
  const [emailMasked, setEmailMasked] = useState('');
  const [countdown, setCountdown] = useState(0);
  const codeInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (step === 1) codeInputRef.current?.focus(); }, [step]);

  const startCountdown = () => {
    setCountdown(60);
    const timer = setInterval(() => { setCountdown((p) => { if (p <= 1) { clearInterval(timer); return 0; } return p - 1; }); }, 1000);
  };

  // ---- Step 1: 账号密码 ----
  const onFinishLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res: any = await adminLoginStep1(values.username, values.password);
      setAdminUser(values.username);
      setEmailMasked(res.email_masked || '');
      message.success('验证码已发送至管理员邮箱');
      startCountdown();
      setStep(1);
    } catch (err: any) { message.error(err.message); } finally { setLoading(false); }
  };

  // ---- Step 2: 邮箱验证码 → Redux dispatch ----
  const onFinishVerify = async (values: { code: string }) => {
    setLoading(true);
    try {
      await dispatch(loginByAdmin({ username: adminUser, code: values.code })).unwrap();
      message.success('验证通过，正在进入管理后台...');
      navigate('/admin/dashboard');
    } catch (err: any) { message.error(err); } finally { setLoading(false); }
  };

  return (
    <div style={styles.container}>
      <div style={styles.leftPanel}>
        <div style={styles.bgGrid} />
        <div style={styles.leftContent}>
          <div style={styles.shieldBox}><SafetyOutlined style={{ fontSize: 56, color: '#fff' }} /></div>
          <Title level={2} style={{ color: '#fff', margin: '32px 0 8px', fontWeight: 600 }}>SmartDesk 管理后台</Title>
          <Paragraph style={{ color: 'rgba(255,255,255,0.6)', fontSize: 15, maxWidth: 340, margin: '0 auto' }}>企业级管理平台，支持用户管理、权限配置、数据监控。</Paragraph>
          <div style={styles.securityFeatures}>
            {[
              { icon: <KeyOutlined />, title: '二次验证', desc: '登录需邮箱验证码确认' },
              { icon: <CheckCircleFilled />, title: 'RBAC 权限', desc: '细粒度角色权限控制' },
              { icon: <SafetyOutlined />, title: '操作审计', desc: '全链路操作日志追踪' },
            ].map((f) => (
              <div key={f.title} style={styles.featureCard}>
                <div style={{ fontSize: 24, color: '#a78bfa', marginBottom: 12 }}>{f.icon}</div>
                <Text strong style={{ color: '#fff', fontSize: 14 }}>{f.title}</Text>
                <Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12, display: 'block', marginTop: 4 }}>{f.desc}</Text>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={styles.rightPanel}>
        <div style={styles.formWrapper}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={styles.miniLogo}><SafetyOutlined style={{ fontSize: 18, color: '#2d1b69' }} /></div>
            <Text strong style={{ fontSize: 16 }}>SmartDesk</Text>
            <span style={styles.adminTag}>管理端</span>
          </div>
          <Title level={4} style={{ margin: '0 0 4px' }}>管理员登录</Title>
          <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>需通过邮箱二次验证</Text>

          <Steps current={step} size="small" style={{ marginBottom: 28 }}
            items={[{ title: '账号密码', icon: step > 0 ? <CheckCircleFilled style={{ color: '#52c41a' }} /> : undefined }, { title: '邮箱验证' }]}
          />

          {step === 0 ? (
            <Form onFinish={onFinishLogin} size="large" autoComplete="off">
              <Form.Item name="username" rules={[{ required: true, message: '请输入管理员账号' }]}>
                <Input prefix={<UserOutlined style={{ color: '#bfbfbf' }} />} placeholder="管理员账号" style={styles.input} />
              </Form.Item>
              <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }, { min: 8, message: '密码至少8位' }]}>
                <Input.Password prefix={<LockOutlined style={{ color: '#bfbfbf' }} />} placeholder="密码" style={styles.input} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block style={styles.loginBtn}>
                  {loading ? '验证中...' : '下一步：发送验证码'}
                </Button>
              </Form.Item>
            </Form>
          ) : (
            <Form onFinish={onFinishVerify} size="large" autoComplete="off">
              {emailMasked && (
                <div style={styles.emailHint}>
                  <MailOutlined style={{ color: '#2d1b69', fontSize: 16 }} />
                  <Text style={{ fontSize: 13 }}>验证码已发送至 <Text strong>{emailMasked}</Text></Text>
                </div>
              )}
              <Form.Item name="code" rules={[{ required: true, message: '请输入验证码' }, { len: 6, message: '验证码为6位数字' }]}>
                <Input ref={codeInputRef as any} prefix={<MailOutlined style={{ color: '#bfbfbf' }} />} placeholder="6位邮箱验证码" maxLength={6}
                  style={{ ...styles.input, textAlign: 'center', fontSize: 20, letterSpacing: 10 }} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block style={styles.loginBtn}>
                  {loading ? '验证中...' : '登录管理后台'}
                </Button>
              </Form.Item>
              <div style={{ textAlign: 'center', marginBottom: 8 }}>
                <Button type="link" disabled={countdown > 0} onClick={() => { if (countdown === 0) { message.success('验证码已重新发送'); startCountdown(); } }}
                  style={{ padding: 0, fontSize: 13, color: '#2d1b69' }}>
                  {countdown > 0 ? `${countdown}s 后可重新发送` : '重新发送验证码'}
                </Button>
              </div>
              <Button type="link" block onClick={() => setStep(0)} style={{ color: '#999', fontSize: 13 }}>← 返回账号密码</Button>
            </Form>
          )}

          <Divider plain><Text type="secondary" style={{ fontSize: 12 }}>安全提示</Text></Divider>
          <div style={styles.securityTip}>
            <SafetyOutlined style={{ color: '#faad14', marginRight: 8 }} />
            <Text type="secondary" style={{ fontSize: 12 }}>管理端登录需二次验证，登录后所有操作将被审计记录。</Text>
          </div>
          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Space><Link to="/login" style={{ fontSize: 13, color: '#999' }}>← 用户端</Link><Text type="secondary">|</Text><Link to="/cs/login" style={{ fontSize: 13, color: '#999' }}>客服端 →</Link></Space>
          </div>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { minHeight: '100vh', display: 'flex' },
  leftPanel: { flex: 1, background: 'linear-gradient(160deg, #0a0a1a 0%, #1a1040 40%, #2d1b69 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' },
  bgGrid: { position: 'absolute', inset: 0, pointerEvents: 'none', backgroundImage: 'linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)', backgroundSize: '40px 40px' },
  leftContent: { position: 'relative', zIndex: 1, textAlign: 'center', padding: 40 },
  shieldBox: { width: 110, height: 110, borderRadius: 28, background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto', border: '2px solid rgba(167,139,250,0.3)' },
  securityFeatures: { display: 'flex', gap: 16, marginTop: 40, justifyContent: 'center' },
  featureCard: { width: 150, padding: '20px 12px', background: 'rgba(255,255,255,0.04)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.06)', textAlign: 'center' },
  rightPanel: { width: 480, background: '#fafbfc', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 },
  formWrapper: { width: '100%', maxWidth: 360 },
  miniLogo: { width: 32, height: 32, borderRadius: 8, background: '#ede9fe', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  adminTag: { marginLeft: 4, fontSize: 11, lineHeight: '18px', padding: '0 6px', borderRadius: 4, background: '#2d1b69', color: '#fff' },
  input: { height: 44, borderRadius: 8 },
  loginBtn: { height: 44, borderRadius: 8, background: 'linear-gradient(135deg, #2d1b69 0%, #a78bfa 100%)', border: 'none', fontWeight: 600, fontSize: 15 },
  emailHint: { display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', background: '#f5f3ff', border: '1px solid #ddd6fe', borderRadius: 8, marginBottom: 20 },
  securityTip: { display: 'flex', alignItems: 'center', padding: '10px 14px', background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 8 },
};

export default AdminLoginPage;
