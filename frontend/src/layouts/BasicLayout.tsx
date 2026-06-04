import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Typography, Space, Avatar, Dropdown } from 'antd';
import {
  MenuFoldOutlined, MenuUnfoldOutlined, DashboardOutlined, TagsOutlined,
  MessageOutlined, TeamOutlined, SafetyOutlined, LogoutOutlined, UserOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { logoutThunk } from '@/store/slices/authSlice';

const { Header, Sider, Content } = Layout;

const BasicLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const [collapsed, setCollapsed] = useState(false);

  const isAdmin = location.pathname.startsWith('/admin');
  const isCS = location.pathname.startsWith('/cs');
  const loginPath = isAdmin ? '/admin/login' : isCS ? '/cs/login' : '/login';

  const menuItems = isAdmin
    ? [
        { key: '/admin/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
        { key: '/admin/users', icon: <TeamOutlined />, label: '用户管理' },
        { key: '/admin/roles', icon: <SafetyOutlined />, label: '角色管理' },
        { key: '/admin/agent-monitor', icon: <RobotOutlined />, label: 'Agent 监控' },
      ]
    : isCS
    ? [
        { key: '/cs/workbench', icon: <DashboardOutlined />, label: '工作台' },
        { key: '/cs/tickets', icon: <TagsOutlined />, label: '工单列表' },
        { key: '/cs/chat', icon: <MessageOutlined />, label: '实时聊天' },
      ]
    : [
        { key: '/dashboard', icon: <DashboardOutlined />, label: '工作台' },
        { key: '/tickets', icon: <TagsOutlined />, label: '我的工单' },
        { key: '/chat', icon: <MessageOutlined />, label: 'AI 问答' },
      ];

  const handleLogout = async () => {
    await dispatch(logoutThunk());
    navigate(loginPath, { replace: true });
  };

  const userMenuItems = [
    { key: 'info', label: <span><UserOutlined /> {user?.nickname || user?.username || '用户'}</span>, disabled: true },
    { type: 'divider' as const },
    { key: 'logout', label: <span style={{ color: '#ff4d4f' }}><LogoutOutlined /> 退出登录</span> },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="dark">
        <div style={{ height: 32, margin: 16, color: '#fff', textAlign: 'center', fontWeight: 'bold', fontSize: collapsed ? 14 : 16 }}>
          {collapsed ? 'SD' : 'SmartDesk'}
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} items={menuItems} onClick={({ key }) => navigate(key)} />
      </Sider>
      <Layout>
        <Header style={{ padding: '0 24px', background: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Button type="text" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed(!collapsed)} />
          <Space>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {isAdmin ? '⚙️ 管理端' : isCS ? '🎧 客服端' : '👤 用户端'}
            </Typography.Text>
            <Dropdown menu={{ items: userMenuItems, onClick: ({ key }) => key === 'logout' && handleLogout() }}>
              <Button type="text" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: isAdmin ? '#2d1b69' : isCS ? '#11998e' : '#667eea' }} />
                <span style={{ fontSize: 13 }}>{user?.nickname || user?.username || '加载中...'}</span>
              </Button>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ margin: 24, background: '#f5f5f5' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default BasicLayout;
