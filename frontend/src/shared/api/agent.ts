/**
 * Agent API — AI Agent 相关接口
 */

import request from './request';

// ============ AI 客服对话 ============

/** AI 客服对话（非流式） */
export const csChat = (message: string, conversationId: string = 'default', userId?: number) =>
  request.post('/agent/cs', { message, conversation_id: conversationId, user_id: userId });

/** AI 客服对话（流式） */
export const csChatStream = (message: string, conversationId: string = 'default', userId?: number) => {
  return fetch('/api/v1/agent/cs/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId, user_id: userId }),
  });
};

// ============ 工单分类 ============

export const classifyTicket = (title: string, content: string) =>
  request.post('/agent/classify', { title, content });

// ============ 优先级分析 ============

export const analyzePriority = (title: string, content: string, userLevel: string = 'normal', complaintCount: number = 0) =>
  request.post('/agent/priority', { title, content, user_level: userLevel, complaint_count: complaintCount });

// ============ 知识库 ============

export const knowledgeQA = (question: string, conversationId: string = 'default', topK: number = 3) =>
  request.post('/agent/knowledge', { question, conversation_id: conversationId, top_k: topK });

export const importDocuments = (texts: string[], chunkSize: number = 500) =>
  request.post('/agent/knowledge/documents', { texts, chunk_size: chunkSize });

export const getKnowledgeStats = () =>
  request.get('/agent/knowledge/stats');

// ============ 智能派单 ============

export const dispatchTicket = (ticketType: string, priority: string = 'medium') =>
  request.post('/agent/dispatch', { ticket_type: ticketType, priority });

// ============ 自动创建工单 ============

export const createTicket = (content: string, conversationId: string = 'default', userId?: number) =>
  request.post('/agent/create-ticket', { content, conversation_id: conversationId, user_id: userId });

// ============ 工作流 ============

export const runWorkflow = (data: {
  ticket_id: number;
  title: string;
  content: string;
  user_id?: number;
  user_level?: string;
  complaint_count?: number;
}) => request.post('/agent/workflow', data);

// ============ LangGraph 工作流 ============

export const runGraphWorkflow = (data: {
  user_question: string;
  conversation_id?: string;
  user_id?: number;
  user_level?: string;
  complaint_count?: number;
}) => request.post('/agent/graph-workflow', data);
