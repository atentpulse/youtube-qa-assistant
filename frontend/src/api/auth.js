import { apiClient, API_BASE_URL } from './client';

export function getGoogleLoginUrl() {
  return `${API_BASE_URL}/auth/google/login`;
}

/**
 * Exchange a single-use OAuth authorization code for access and refresh tokens.
 * Backend contract: POST /auth/oauth/exchange
 */
export function exchangeOAuthCode(code, opts) {
  return apiClient.post('/auth/oauth/exchange', { code }, opts);
}

/**
 * Logout the authenticated user and invalidate all active sessions on the server.
 * Backend contract: POST /auth/logout
 */
export function logoutUser(opts) {
  return apiClient.post('/auth/logout', {}, opts);
}

/**
 * Returns the currently authenticated user based on the active token.
 * Throws ApiError with status 401 if invalid/expired.
 */
export function getCurrentUser(opts) {
  return apiClient.get('/auth/me', opts);
}

/**
 * Sign in using email and password credentials.
 * Backend contract: POST /auth/login
 */
export function loginWithCredentials({ email, password }, opts) {
  return apiClient.post('/auth/login', { email, password }, opts);
}

/**
 * Register a new user with email and password credentials.
 * Backend contract: POST /auth/register
 */
export function registerWithCredentials({ email, password, username }, opts) {
  return apiClient.post('/auth/register', { email, password, username }, opts);
}

/**
 * Refresh an existing authentication token.
 * Backend contract: POST /auth/refresh
 */
export function refreshToken(data = {}, opts) {
  const body = data?.refresh_token ? { refresh_token: data.refresh_token } : {};
  return apiClient.post('/auth/refresh', body, opts);
}

/**
 * Update authenticated user's profile display name.
 * Backend contract: PATCH /auth/me
 */
export function updateProfile({ username }, opts) {
  return apiClient.patch('/auth/me', { username }, opts);
}

/**
 * Delete authenticated user's account and data.
 * Backend contract: DELETE /auth/me
 */
export function deleteAccount(opts) {
  return apiClient.delete('/auth/me', opts);
}

