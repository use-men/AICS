/**
 * Ticket API — 工单系统接口
 */

import request from './request';

// ---- 创建工单 ----
export const createTicket = (data: { title: string; content: string; ticket_type: string }) =>
  request.post('/tickets', data);

// ---- 工单列表 ----
export const fetchTickets = (params?: {
  page?: number;
  status?: string;
  ticket_type?: string;
  priority?: string;
}) => request.get('/tickets', { params });

// ---- 工单详情 ----
export const getTicketDetail = (id: number) =>
  request.get(`/tickets/${id}`);

// ---- 删除工单 ----
export const deleteTicket = (id: number) =>
  request.delete(`/tickets/${id}`);

// ---- 更新状态 ----
export const updateTicketStatus = (id: number, status: string) =>
  request.put(`/tickets/${id}/status`, { status });

// ---- 分配工单 ----
export const assignTicket = (id: number, serviceId: number) =>
  request.put(`/tickets/${id}/assign`, { service_id: serviceId });

// ---- 接单 ----
export const acceptTicket = (id: number) =>
  request.put(`/tickets/${id}/accept`);

// ---- 回复工单 ----
export const replyTicket = (id: number, content: string) =>
  request.post(`/tickets/${id}/replies`, { content });

// ---- 工单统计 ----
export const getTicketStats = () =>
  request.get('/tickets/stats/overview');

// ---- 管理端大屏统计 ----
export const getDashboardStats = () =>
  request.get('/tickets/stats/dashboard');

// ---- AI 推荐回复 ----
export const suggestCSReply = (ticketId: number) =>
  request.post('/agent/cs-reply-suggest', { ticket_id: ticketId });

// ---- 批量未读消息数 ----
export const getUnreadCounts = (ticketIds: number[], readerType: 'user' | 'service') =>
  request.get('/chat/unread-batch', { params: { ticket_ids: ticketIds.join(','), reader_type: readerType } });
