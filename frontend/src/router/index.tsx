import { lazy } from 'react';
import type { RouteObject } from 'react-router-dom';
import BasicLayout from '../layouts/BasicLayout';
import AuthGuard from './AuthGuard';

// ---- Lazy pages ----
const LoginPage     = lazy(() => import('../client/pages/LoginPage'));
const Dashboard     = lazy(() => import('../client/pages/DashboardPage'));
const TicketList    = lazy(() => import('../client/pages/TicketListPage'));
const TicketDetail  = lazy(() => import('../client/pages/TicketDetailPage'));
const AIChat        = lazy(() => import('../client/pages/AIChatPage'));
const Settings      = lazy(() => import('../client/pages/SettingsPage'));

const CSLogin       = lazy(() => import('../customer-service/pages/LoginPage'));
const CSWorkbench   = lazy(() => import('../customer-service/pages/WorkbenchPage'));
const CSTickets     = lazy(() => import('../customer-service/pages/TicketListPage'));
const CSTools       = lazy(() => import('../customer-service/pages/ToolsPage'));

const AdminLogin    = lazy(() => import('../admin/pages/LoginPage'));
const AdminDash     = lazy(() => import('../admin/pages/DashboardPage'));
const AdminUsers    = lazy(() => import('../admin/pages/UserManagementPage'));
const AdminAgents   = lazy(() => import('../admin/pages/AgentManagementPage'));
const AgentMonitor  = lazy(() => import('../admin/pages/AgentMonitorPage'));
const TraceDetail   = lazy(() => import('../admin/pages/TraceDetailPage'));

// ---- Route config ----
export const appRoutes: RouteObject[] = [
  // ==================== 用户端 ====================
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <AuthGuard><BasicLayout /></AuthGuard>,
    children: [
      { index: true, element: <AIChat /> },
      { path: 'chat', element: <AIChat /> },
      { path: 'dashboard', element: <AIChat /> },
      { path: 'tickets', element: <TicketList /> },
      { path: 'tickets/:id', element: <TicketDetail /> },
      { path: 'settings', element: <Settings /> },
    ],
  },

  // ==================== 客服端 ====================
  {
    path: '/cs/login',
    element: <CSLogin />,
  },
  {
    path: '/cs',
    element: <AuthGuard><BasicLayout /></AuthGuard>,
    children: [
      { index: true, element: <CSWorkbench /> },
      { path: 'workbench', element: <CSWorkbench /> },
      { path: 'tickets', element: <CSTickets /> },
      { path: 'tickets/:id', element: <TicketDetail /> },
      { path: 'tools', element: <CSTools /> },
    ],
  },

  // ==================== 管理端 ====================
  {
    path: '/admin/login',
    element: <AdminLogin />,
  },
  {
    path: '/admin',
    element: <AuthGuard><BasicLayout /></AuthGuard>,
    children: [
      { index: true, element: <AdminDash /> },
      { path: 'dashboard', element: <AdminDash /> },
      { path: 'users', element: <AdminUsers /> },
      { path: 'agents', element: <AdminAgents /> },
      { path: 'agent-monitor', element: <AgentMonitor /> },
      { path: 'agent-monitor/:traceId', element: <TraceDetail /> },
    ],
  },

  // ==================== 404 ====================
  {
    path: '*',
    element: <div style={{ textAlign: 'center', paddingTop: 120 }}><h1>404</h1><p>页面不存在</p></div>,
  },
];
