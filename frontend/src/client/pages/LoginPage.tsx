import { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Typography, Space, Tabs, Checkbox, message, Divider } from 'antd';
import {
  MobileOutlined, LockOutlined, MailOutlined, SafetyCertificateOutlined,
  RobotOutlined, WechatOutlined, QqOutlined, GlobalOutlined, SunOutlined, MoonOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAppDispatch } from '@/store/hooks';
import { loginByPhone, loginByEmail } from '@/store/slices/authSlice';
import { sendSmsCode } from '@/shared/api/auth';
import { useTheme } from '@/locales/theme';

const { Title, Text, Paragraph } = Typography;
type LoginMode = 'phone' | 'email';

const ClientLoginPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { mode, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [mode2, setMode] = useState<LoginMode>('phone');
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [phoneValue, setPhoneValue] = useState('');
  const [form] = Form.useForm();

  const isDark = mode === 'dark';
  const bgColor = isDark ? '#1a1a2e' : undefined;
  const cardBg = isDark ? '#16213e' : '#fff';

  const toggleLanguage = () => i18n.changeLanguage(i18n.language === 'zh' ? 'en' : 'zh');

  const startCountdown = useCallback(() => {
    setCountdown(60);
    const timer = setInterval(() => {
      setCountdown((p) => { if (p <= 1) { clearInterval(timer); return 0; } return p - 1; });
    }, 1000);
  }, []);

  const handleSendCode = useCallback(async () => {
    if (!phoneValue || phoneValue.length !== 11) { message.warning(t('login.phonePlaceholder')); return; }
    try {
      await sendSmsCode(phoneValue);
      message.success(t('common.success'));
      startCountdown();
    } catch (err: any) { message.error(err.message || t('common.error')); }
  }, [phoneValue, startCountdown, t]);

  const onPhoneLogin = async (values: { phone: string; code: string; remember?: boolean }) => {
    setLoading(true);
    try {
      await dispatch(loginByPhone({ ...values, remember: values.remember !== false })).unwrap();
      message.success(t('common.success'));
      navigate('/dashboard');
    } catch (err: any) { message.error(err); } finally { setLoading(false); }
  };

  const onEmailLogin = async (values: { email: string; password: string; remember?: boolean }) => {
    setLoading(true);
    try {
      await dispatch(loginByEmail({ ...values, remember: values.remember !== false })).unwrap();
      message.success(t('common.success'));
      navigate('/dashboard');
    } catch (err: any) { message.error(err); } finally { setLoading(false); }
  };

  return (
    <div style={styles.container}>
      {/* 右上角工具栏 */}
      <div style={{ position: 'absolute', top: 16, right: 16, display: 'flex', gap: 8, zIndex: 10 }}>
        <Button type="text" icon={<GlobalOutlined />} onClick={toggleLanguage} style={{ color: '#fff' }}>
          {i18n.language === 'zh' ? 'EN' : '中'}
        </Button>
        <Button type="text" icon={isDark ? <SunOutlined /> : <MoonOutlined />} onClick={toggleTheme} style={{ color: '#fff' }} />
      </div>

      <div style={styles.leftPanel}>
        <div style={styles.brandContent}>
          <div style={styles.logoBox}><RobotOutlined style={{ fontSize: 48, color: '#fff' }} /></div>
          <Title level={2} style={{ color: '#fff', margin: '24px 0 8px' }}>{t('login.brand')}</Title>
          <Paragraph style={{ color: 'rgba(255,255,255,0.8)', fontSize: 16, maxWidth: 320 }}>
            {t('login.brandDesc')}
          </Paragraph>
          <div style={styles.featureList}>
            {[t('login.features.aiChat'), t('login.features.autoRoute'), t('login.features.realtime'), t('login.features.security')].map((f) => (
              <div key={f} style={styles.featureItem}>{f}</div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ ...styles.rightPanel, background: cardBg }}>
        <div style={styles.formWrapper}>
          <div style={{ marginBottom: 32 }}>
            <Title level={3} style={{ margin: 0 }}>{t('login.welcome')}</Title>
            <Text type="secondary">{t('login.subtitle')}</Text>
          </div>

          <Tabs activeKey={mode2} onChange={(k) => setMode(k as LoginMode)} centered items={[
            {
              key: 'phone',
              label: <span><MobileOutlined /> {t('login.phoneLogin')}</span>,
              children: (
                <Form onFinish={onPhoneLogin} size="large" autoComplete="off">
                  <Form.Item name="phone" rules={[{ required: true, message: t('login.phonePlaceholder') }, { pattern: /^1[3-9]\d{9}$/, message: t('login.phonePlaceholder') }]}>
                    <Input prefix={<MobileOutlined style={{ color: '#bfbfbf' }} />} placeholder={t('login.phonePlaceholder')} maxLength={11} value={phoneValue} onChange={(e) => setPhoneValue(e.target.value)} />
                  </Form.Item>
                  <Form.Item name="code" rules={[{ required: true, message: t('login.verificationCodePlaceholder') }, { len: 6, message: t('login.verificationCodePlaceholder') }]}>
                    <Input prefix={<SafetyCertificateOutlined style={{ color: '#bfbfbf' }} />} placeholder={t('login.verificationCodePlaceholder')} maxLength={6}
                      suffix={<Button type="link" size="small" disabled={countdown > 0} onClick={handleSendCode} style={{ padding: 0, fontSize: 13 }}>{countdown > 0 ? `${countdown}${t('login.resendAfter')}` : t('login.sendCode')}</Button>}
                    />
                  </Form.Item>
                  <Form.Item>
                    <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 16 }}>
                      <Form.Item name="remember" valuePropName="checked" noStyle>
                        <Checkbox style={{ fontSize: 14 }}>{t('login.rememberMe')}</Checkbox>
                      </Form.Item>
                    </div>
                    <Button type="primary" htmlType="submit" loading={loading} block style={styles.primaryBtn}>{t('common.login')}</Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'email',
              label: <span><MailOutlined /> {t('login.emailLogin')}</span>,
              children: (
                <Form onFinish={onEmailLogin} size="large" autoComplete="off">
                  <Form.Item name="email" rules={[{ required: true, message: t('login.emailPlaceholder') }, { pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: t('login.emailPlaceholder') }]}>
                    <Input prefix={<MailOutlined style={{ color: '#bfbfbf' }} />} placeholder={t('login.emailPlaceholder')} />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, message: t('login.passwordPlaceholder') }, { min: 6, message: t('login.passwordPlaceholder') }]}>
                    <Input.Password prefix={<LockOutlined style={{ color: '#bfbfbf' }} />} placeholder={t('login.passwordPlaceholder')} />
                  </Form.Item>
                  <Form.Item>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                      <Form.Item name="remember" valuePropName="checked" noStyle>
                        <Checkbox style={{ fontSize: 14 }}>{t('login.rememberMe')}</Checkbox>
                      </Form.Item>
                      <a style={{ fontSize: 14 }}>{t('login.forgotPassword')}</a>
                    </div>
                    <Button type="primary" htmlType="submit" loading={loading} block style={styles.primaryBtn}>{t('common.login')}</Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]} />

          <Divider plain><Text type="secondary" style={{ fontSize: 12 }}>{t('login.otherLogin')}</Text></Divider>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 24, marginBottom: 24 }}>
            <div style={styles.socialIcon}><WechatOutlined style={{ fontSize: 20, color: '#07c160' }} /></div>
            <div style={styles.socialIcon}><QqOutlined style={{ fontSize: 20, color: '#12b7f5' }} /></div>
            <div style={styles.socialIcon}><MailOutlined style={{ fontSize: 20, color: '#ea4335' }} /></div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <Space>
              <Link to="/cs/login" style={styles.switchLink}>{t('login.switchToCS')}</Link>
              <Text type="secondary">|</Text>
              <Link to="/admin/login" style={styles.switchLink}>{t('login.switchToAdmin')}</Link>
            </Space>
          </div>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { minHeight: '100vh', display: 'flex', position: 'relative' },
  leftPanel: { flex: 1, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 },
  brandContent: { position: 'relative', zIndex: 1, textAlign: 'center' },
  logoBox: { width: 96, height: 96, borderRadius: 24, background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(10px)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto' },
  featureList: { marginTop: 32, display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center' },
  featureItem: { color: 'rgba(255,255,255,0.9)', fontSize: 15, padding: '8px 20px', background: 'rgba(255,255,255,0.1)', borderRadius: 8 },
  rightPanel: { width: 480, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 },
  formWrapper: { width: '100%', maxWidth: 360 },
  primaryBtn: { height: 44, borderRadius: 8, fontWeight: 500 },
  socialIcon: { width: 40, height: 40, borderRadius: '50%', border: '1px solid #e8e8e8', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' },
  switchLink: { fontSize: 13, color: '#667eea' },
};

export default ClientLoginPage;
