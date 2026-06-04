import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Typography, Checkbox, message, Tag, Space } from 'antd';
import { UserOutlined, LockOutlined, CustomerServiceOutlined, DashboardOutlined, TeamOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useAppDispatch } from '@/store/hooks';
import { loginByCS } from '@/store/slices/authSlice';

const { Title, Text, Paragraph } = Typography;

const CSLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: { employee_id: string; password: string; remember?: boolean }) => {
    setLoading(true);
    try {
      await dispatch(loginByCS({ ...values, remember: values.remember !== false })).unwrap();
      message.success('登录成功，正在进入工作台...');
      navigate('/cs/workbench');
    } catch (err: any) {
      message.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.leftPanel}>
        <div style={styles.bgDecoration}>
          {[...Array(5)].map((_, i) => (
            <div key={i} style={{ position: 'absolute', width: 200 + i * 100, height: 200 + i * 100, borderRadius: '50%', border: '1px solid rgba(255,255,255,0.08)', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }} />
          ))}
        </div>
        <div style={styles.leftContent}>
          <div style={styles.csIconBox}><CustomerServiceOutlined style={{ fontSize: 56, color: '#fff' }} /></div>
          <Title level={2} style={{ color: '#fff', margin: '32px 0 8px', fontWeight: 600 }}>SmartDesk 客服工作台</Title>
          <Paragraph style={{ color: 'rgba(255,255,255,0.7)', fontSize: 15, maxWidth: 360, margin: '0 auto' }}>高效处理客户工单，AI 辅助智能回复，实时协作提升服务质量。</Paragraph>
          <div style={styles.statsRow}>
            {[
              { icon: <DashboardOutlined />, label: '工单处理', value: '1,234' },
              { icon: <TeamOutlined />, label: '在线坐席', value: '12' },
              { icon: <ThunderboltOutlined />, label: '平均响应', value: '<30s' },
            ].map((s) => (
              <div key={s.label} style={styles.statCard}>
                <div style={{ fontSize: 20, color: '#52c41a', marginBottom: 8 }}>{s.icon}</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#fff' }}>{s.value}</div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={styles.rightPanel}>
        <div style={styles.formWrapper}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={styles.miniLogo}><CustomerServiceOutlined style={{ fontSize: 18, color: '#11998e' }} /></div>
            <Text strong style={{ fontSize: 16 }}>SmartDesk</Text>
            <Tag color="green" style={{ marginLeft: 4, fontSize: 11, lineHeight: '18px', padding: '0 6px' }}>客服端</Tag>
          </div>
          <Title level={4} style={{ margin: '0 0 4px' }}>客服工作台登录</Title>
          <Text type="secondary" style={{ display: 'block', marginBottom: 32 }}>使用工号和密码登录客服系统</Text>

          <Form onFinish={onFinish} size="large" initialValues={{ remember: true }} autoComplete="off">
            <Form.Item name="employee_id" rules={[{ required: true, message: '请输入工号' }, { pattern: /^cs_\d{4,}$/, message: '工号格式：cs_XXXX' }]}>
              <Input prefix={<UserOutlined style={{ color: '#bfbfbf' }} />} placeholder="工号（如 cs_1001）" style={styles.input} />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password prefix={<LockOutlined style={{ color: '#bfbfbf' }} />} placeholder="密码" style={styles.input} />
            </Form.Item>
            <Form.Item>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <Form.Item name="remember" valuePropName="checked" noStyle><Checkbox style={{ fontSize: 14 }}>记住登录状态</Checkbox></Form.Item>
                <a style={{ fontSize: 13, color: '#11998e' }}>忘记密码？</a>
              </div>
              <Button type="primary" htmlType="submit" loading={loading} block style={styles.loginBtn}>
                {loading ? '登录中...' : '登录工作台'}
              </Button>
            </Form.Item>
          </Form>

          <div style={styles.tipBox}>
            <Text type="secondary" style={{ fontSize: 12 }}>测试账号：<Text strong style={{ color: '#11998e' }}>cs_1001</Text> / <Text strong style={{ color: '#11998e' }}>123456</Text></Text>
          </div>
          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Space><Link to="/login" style={{ fontSize: 13, color: '#999' }}>← 用户端登录</Link><Text type="secondary">|</Text><Link to="/admin/login" style={{ fontSize: 13, color: '#999' }}>管理端 →</Link></Space>
          </div>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { minHeight: '100vh', display: 'flex' },
  leftPanel: { flex: 1, background: 'linear-gradient(160deg, #0a2e1f 0%, #11998e 50%, #38ef7d 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' },
  bgDecoration: { position: 'absolute', inset: 0, pointerEvents: 'none' },
  leftContent: { position: 'relative', zIndex: 1, textAlign: 'center', padding: 40 },
  csIconBox: { width: 110, height: 110, borderRadius: 28, background: 'rgba(255,255,255,0.12)', backdropFilter: 'blur(12px)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto', border: '2px solid rgba(255,255,255,0.15)' },
  statsRow: { display: 'flex', gap: 20, marginTop: 40, justifyContent: 'center' },
  statCard: { width: 130, padding: '20px 12px', background: 'rgba(255,255,255,0.08)', backdropFilter: 'blur(10px)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.1)', textAlign: 'center' },
  rightPanel: { width: 480, background: '#fafbfc', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 },
  formWrapper: { width: '100%', maxWidth: 360 },
  miniLogo: { width: 32, height: 32, borderRadius: 8, background: '#e6fff9', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  input: { height: 44, borderRadius: 8 },
  loginBtn: { height: 44, borderRadius: 8, background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)', border: 'none', fontWeight: 600, fontSize: 15 },
  tipBox: { marginTop: 16, padding: '10px 14px', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 8, textAlign: 'center' },
};

export default CSLoginPage;
