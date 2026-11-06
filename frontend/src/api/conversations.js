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

export function createConversation({ title = 'New Chat', video_id = null } = {}, opts) {
  const body = { title };
  if (video_id) body.video_id = video_id;
  return apiClient.post('/conversations', body, opts);
}

export function renameConversation(id, title, opts) {
  return apiClient.patch(`/conversations/${id}`, { title }, opts);
}

export function deleteConversation(id, opts) {
  return apiClient.delete(`/conversations/${id}`, opts);
}

/**
 * Clear all conversations for the authenticated user.
 * Backend contract: DELETE /conversations
 */
export function clearAllConversations(opts) {
  return apiClient.delete('/conversations', opts);
}

/**
 * Export full conversation history with messages.
 * Backend contract: GET /conversations/export
 */
export function exportConversations(opts) {
  return apiClient.get('/conversations/export', opts);
}
