import { apiClient } from './client';

/**
 * Submits an authenticated bug report to the backend.
 * @param {Object} data - { title: string, description: string, category?: string }
 * @returns {Promise<Object>} Created bug report record
 */
export async function submitBugReport({ title, description, category = 'general' }) {
  const response = await apiClient.post('/api/support/bug-reports', {
    title,
    description,
    category,
  });
  return response.data;
}
