import { apiClient } from './client';

export function listConversations(opts) {
  return apiClient.get('/conversations', opts);
}

export function getConversations(opts) {
  return apiClient.get('/conversations', opts);
}

export function getConversation(id, opts) {
  return apiClient.get(`/conversations/${id}`, opts);
}

/**
 * Fetch paginated messages for a conversation.
 * Backend contract: GET /conversations/{id}/messages?before_id=<int>
 */
export function getConversationMessages(id, opts = {}) {
  const { beforeId, ...rest } = opts || {};
  const params = beforeId !== undefined && beforeId !== null ? { before_id: beforeId } : undefined;
  return apiClient.get(`/conversations/${id}/messages`, { ...rest, params });
}

export function createConversation({ title = 'New Chat' } = {}, opts) {
  return apiClient.post('/conversations', { title }, opts);
}

export function renameConversation(id, title, opts) {
  return apiClient.patch(`/conversations/${id}`, { title }, opts);
}

export function deleteConversation(id, opts) {
  return apiClient.delete(`/conversations/${id}`, opts);
}
