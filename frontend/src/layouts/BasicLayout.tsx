/**
 * BasicLayout — 三端共享布局（支持国际化 + 主题切换）
 */

import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Typography, Space, Avatar, Dropdown, Tooltip } from 'antd';
import {
  MenuFoldOutlined, MenuUnfoldOutlined, DashboardOutlined, TagsOutlined,
  MessageOutlined, TeamOutlined, SafetyOutlined, LogoutOutlined, UserOutlined,
  RobotOutlined, SunOutlined, MoonOutlined, GlobalOutlined, SettingOutlined,
  CustomerServiceOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { logoutThunk } from '@/store/slices/authSlice';
import { useTheme } from '@/locales/theme';

const { Header, Sider, Content } = Layout;

const BasicLayout: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const { mode, toggleTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(window.innerWidth < 768);

  // 小屏自动收起侧边栏
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) setCollapsed(true);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isAdmin = location.pathname.startsWith('/admin');
  const isCS = location.pathname.startsWith('/cs');
  const loginPath = isAdmin ? '/admin/login' : isCS ? '/cs/login' : '/login';

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language === 'zh' ? 'en' : 'zh');
  };

  const menuItems = isAdmin
    ? [
        { key: '/admin/dashboard', icon: <DashboardOutlined />, label: t('menu.dashboard') },
        { key: '/admin/users', icon: <TeamOutlined />, label: t('menu.users') },
        { key: '/admin/agents', icon: <CustomerServiceOutlined />, label: '客服管理' },
        { key: '/admin/agent-monitor', icon: <RobotOutlined />, label: t('menu.agentMonitor') },
      ]
    : isCS
    ? [
        { key: '/cs/workbench', icon: <DashboardOutlined />, label: t('menu.dashboard') },
        { key: '/cs/tickets', icon: <TagsOutlined />, label: t('menu.ticketList') },
        { key: '/cs/tools', icon: <SettingOutlined />, label: '快捷工具' },
      ]
    : [
        { key: '/chat', icon: <RobotOutlined />, label: t('menu.aiChat') },
        { key: '/tickets', icon: <TagsOutlined />, label: t('menu.tickets') },
      ];

  const handleLogout = async () => {
    await dispatch(logoutThunk());
    navigate(loginPath, { replace: true });
  };

  const userMenuItems = [
    { key: 'info', label: <span><UserOutlined /> {user?.nickname || user?.username || t('common.loading')}</span>, disabled: true },
    { type: 'divider' as const },
    { key: 'settings', label: <span><SettingOutlined /> 个人设置</span> },
    { key: 'logout', label: <span style={{ color: '#ff4d4f' }}><LogoutOutlined /> {t('common.logout')}</span> },
  ];

  // 深色模式下的统一背景色
  const darkBg = '#1a1a1a';
  const darkBorder = '#303030';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="light"
        style={{
          background: mode === 'dark' ? darkBg : undefined,
          borderRight: mode === 'dark' ? `1px solid ${darkBorder}` : undefined,
        }}
      >
        <div style={{
          height: 32,
          margin: 16,
          color: mode === 'dark' ? '#fff' : '#000',
          textAlign: 'center',
          fontWeight: 'bold',
          fontSize: collapsed ? 14 : 16,
        }}>
          {collapsed ? 'SD' : 'SmartDesk'}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            background: mode === 'dark' ? darkBg : undefined,
            borderInlineEnd: 'none',
          }}
          theme={mode === 'dark' ? 'dark' : 'light'}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 24px',
          background: mode === 'dark' ? darkBg : '#fff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: mode === 'dark' ? `1px solid ${darkBorder}` : '1px solid #f0f0f0',
        }}>
          <Button type="text" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed(!collapsed)} />
          <Space size="middle">
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {isAdmin ? '⚙️ ' : isCS ? '🎧 ' : '👤 '}{t(`portal.${isAdmin ? 'admin' : isCS ? 'cs' : 'client'}`)}
            </Typography.Text>

            {/* 语言切换 */}
            <Tooltip title={i18n.language === 'zh' ? 'English' : '中文'}>
              <Button type="text" size="small" icon={<GlobalOutlined />} onClick={toggleLanguage}>
                {i18n.language === 'zh' ? 'EN' : '中'}
              </Button>
            </Tooltip>

            {/* 主题切换 */}
            <Tooltip title={mode === 'light' ? 'Dark Mode' : 'Light Mode'}>
              <Button type="text" size="small" icon={mode === 'light' ? <MoonOutlined /> : <SunOutlined />} onClick={toggleTheme} />
            </Tooltip>

            {/* 用户菜单 */}
            <Dropdown menu={{
              items: userMenuItems,
              onClick: ({ key }) => {
                if (key === 'logout') handleLogout();
                else if (key === 'settings') navigate('/settings');
              },
            }}>
              <Button type="text" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Avatar
                  size={32}
                  src={user?.avatar}
                  icon={!user?.avatar && <UserOutlined />}
                  style={{ backgroundColor: isAdmin ? '#2d1b69' : isCS ? '#11998e' : '#667eea' }}
                />
                <span style={{ fontSize: 14 }}>{user?.nickname || user?.username || t('common.loading')}</span>
              </Button>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ margin: window.innerWidth < 768 ? 12 : 24, background: mode === 'dark' ? '#121212' : '#f5f5f5' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default BasicLayout;
