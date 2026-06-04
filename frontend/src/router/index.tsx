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

const CSLogin       = lazy(() => import('../customer-service/pages/LoginPage'));
const CSWorkbench   = lazy(() => import('../customer-service/pages/WorkbenchPage'));
const CSTickets     = lazy(() => import('../customer-service/pages/TicketListPage'));

const AdminLogin    = lazy(() => import('../admin/pages/LoginPage'));
const AdminDash     = lazy(() => import('../admin/pages/DashboardPage'));
const AdminUsers    = lazy(() => import('../admin/pages/UserManagementPage'));
const AdminRoles    = lazy(() => import('../admin/pages/RoleManagementPage'));
const AgentMonitor  = lazy(() => import('../admin/pages/AgentMonitorPage'));

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
      { index: true, element: <Dashboard /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'tickets', element: <TicketList /> },
      { path: 'tickets/:id', element: <TicketDetail /> },
      { path: 'chat', element: <AIChat /> },
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
      { path: 'chat', element: <AIChat /> },
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
      { path: 'roles', element: <AdminRoles /> },
      { path: 'agent-monitor', element: <AgentMonitor /> },
    ],
  },

  // ==================== 404 ====================
  {
    path: '*',
    element: <div style={{ textAlign: 'center', paddingTop: 120 }}><h1>404</h1><p>页面不存在</p></div>,
  },
];
