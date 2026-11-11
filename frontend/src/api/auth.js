import { apiClient, API_BASE_URL } from './client.js';

export function getGoogleLoginUrl() {
  return `${API_BASE_URL}/auth/google/login`;
}

// Active in-flight exchange promises by code to prevent concurrent duplicate requests
const inFlightExchanges = new Map();
// Cache of successfully completed code exchanges to prevent repeat network calls on remount
const completedExchanges = new Map();
// Set of consumed or failed single-use codes that must not be retried
const consumedCodes = new Set();

/**
 * Exchange a single-use OAuth authorization code for access and refresh tokens.
 * Backend contract: POST /auth/oauth/exchange
 *
 * Guard behavior:
 * 1. Single-use codes are dispatched over the wire strictly once.
 * 2. If an exchange for the code is already pending (e.g. React StrictMode or concurrent effects),
 *    the active in-flight Promise is reused.
 * 3. If the code was already consumed in this session, the cached token response is returned.
 * 4. Consumed/rejected codes are recorded to prevent useless retries.
 */
export function exchangeOAuthCode(code, opts) {
  if (!code) {
    return Promise.reject(new Error('No authorization code provided.'));
  }

  // 1. Return cached result if already consumed successfully in this session
  if (completedExchanges.has(code)) {
    return Promise.resolve(completedExchanges.get(code));
  }

  // 2. Reject immediately if code is known to be consumed / rejected
  if (consumedCodes.has(code)) {
    return Promise.reject(new Error('Authorization code has already been consumed.'));
  }

  // 3. Return active in-flight promise if exchange is already pending
  if (inFlightExchanges.has(code)) {
    return inFlightExchanges.get(code);
  }

  // 4. Initiate single exchange request
  const exchangePromise = apiClient
    .post('/auth/oauth/exchange', { code }, opts)
    .then((data) => {
      completedExchanges.set(code, data);
      consumedCodes.add(code);
      inFlightExchanges.delete(code);
      return data;
    })
    .catch((err) => {
      inFlightExchanges.delete(code);
      // Mark code as consumed on 400 (single-use replay or invalid/expired) to stop retries
      if (err?.status === 400) {
        consumedCodes.add(code);
      }
      throw err;
    });

  inFlightExchanges.set(code, exchangePromise);
  return exchangePromise;
}

/**
 * Resets the in-memory exchange cache (used for unit tests and session cleanups).
 */
export function _resetOAuthExchangeCache() {
  inFlightExchanges.clear();
  completedExchanges.clear();
  consumedCodes.clear();
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

/**
 * Verify user email address with single-use verification token.
 * Backend contract: GET /auth/verify-email?token=...
 */
export function verifyEmail(token, opts) {
  return apiClient.get('/auth/verify-email', { ...opts, params: { token } });
}

/**
 * Request a password reset link for the given email address.
 * Backend contract: POST /auth/forgot-password
 */
export function forgotPassword(email, opts) {
  return apiClient.post('/auth/forgot-password', { email }, opts);
}

/**
 * Reset password using single-use reset token and new password.
 * Backend contract: POST /auth/reset-password
 */
export function resetPassword({ token, new_password }, opts) {
  return apiClient.post('/auth/reset-password', { token, new_password }, opts);
}

/**
 * Request a new verification email for an unverified account.
 * Backend contract: POST /auth/resend-verification
 */
export function resendVerification(email, opts) {
  return apiClient.post('/auth/resend-verification', { email }, opts);
}

/**
 * Send a 6-digit login OTP code to the provided email address.
 * Backend contract: POST /auth/otp/send
 */
export function sendLoginOtp(email, opts) {
  return apiClient.post('/auth/otp/send', { email }, opts);
}

/**
 * Verify a 6-digit login OTP code and obtain session tokens.
 * Backend contract: POST /auth/otp/verify
 */
export function verifyLoginOtp({ email, otp }, opts) {
  return apiClient.post('/auth/otp/verify', { email, otp }, opts);
}

