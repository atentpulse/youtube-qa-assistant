import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getCurrentUser, loginWithCredentials, registerWithCredentials, refreshToken } from '../api/auth';
import { apiClient } from '../api/client';
import { getToken, setToken as persistToken, clearToken } from '../utils/tokenStorage';

const AuthContext = createContext(null);

// 'initializing' — startup restoreSession() hasn't resolved yet.
// 'authenticated' — valid token + user loaded.
// 'unauthenticated' — no token, or the token was rejected/cleared.
//
// Sessions are established three ways: email/password login (JWT),
// email registration followed by email verification + sign in, and
// completeOAuthLogin(), called by OAuthCallbackPage once the
// backend has redirected back with a JWT already issued.
export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => getToken());
  const [user, setUser] = useState(null);
  const [authStatus, setAuthStatus] = useState('initializing');
  // Set only when a session ends involuntarily (a 401 from an existing
  // session), never on a normal user-initiated logout — LoginPage shows
  // this once, then it's cleared.
  const [sessionMessage, setSessionMessage] = useState(null);

  const isAuthenticated = authStatus === 'authenticated' && !!user;
  const loading = authStatus === 'initializing';

  const restoreSession = useCallback(async () => {
    const storedToken = getToken();

    if (!storedToken) {
      setAuthStatus('unauthenticated');
      return;
    }

    setTokenState(storedToken);
    // Keep the API client's in-memory token in sync with persisted storage,
    // otherwise the Authorization header is never attached after a reload.
    apiClient.setToken(storedToken);

    try {
      const me = await getCurrentUser();
      setUser(me);
      setAuthStatus('authenticated');
    } catch {
      // Token missing/invalid/expired (401) or unreachable backend — either
      // way we can't trust it. api/client.js already clears it from storage
      // on a 401; clear it here too in case this failed for another reason.
      clearToken();
      setTokenState(null);
      setUser(null);
      setAuthStatus('unauthenticated');
    }
  }, []);

  // Restore session once on startup.
  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  // A 401 from ANY request (dispatched centrally by api/client.js) means
  // the token is no longer valid. Storage is already cleared by client.js;
  // this keeps in-memory auth state in sync and surfaces a friendly
  // "session expired" message on the next /login render. ProtectedRoute
  // reacts to isAuthenticated becoming false and redirects there itself —
  // this handler does not navigate, avoiding any redirect-loop risk.
  useEffect(() => {
    const onUnauthorized = () => {
      setTokenState(null);
      setUser(null);
      setAuthStatus('unauthenticated');
      setSessionMessage('Your session has expired. Please sign in again.');
    };
    window.addEventListener('auth:unauthorized', onUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', onUnauthorized);
  }, []);

  /**
   * Completes the Google OAuth flow. The backend has already verified the
   * user with Google and issued a JWT, redirecting the browser to
   * /oauth/callback?token=<jwt>. This stores that token through the same
   * centralized tokenStorage used everywhere else, then restores the user
   * via GET /auth/me — the same restoration path used on a normal reload.
   * Throws on failure so the callback page can show its own error state;
   * auth state is left cleared either way.
   */
  const completeOAuthLogin = useCallback(async (rawToken) => {
    persistToken(rawToken);
    setTokenState(rawToken);
    apiClient.setToken(rawToken);

    try {
      const me = await getCurrentUser();
      setUser(me);
      setAuthStatus('authenticated');
      setSessionMessage(null);
      return me;
    } catch (err) {
      clearToken();
      setTokenState(null);
      setUser(null);
      setAuthStatus('unauthenticated');
      throw err;
    }
  }, []);

  const login = useCallback(async ({ email, password }) => {
    const res = await loginWithCredentials({ email, password });
    const rawToken = res?.access_token || res?.token;
    if (!rawToken) {
      throw new Error('No access token returned by server.');
    }
    persistToken(rawToken);
    setTokenState(rawToken);
    apiClient.setToken(rawToken);
    if (res.user) {
      setUser(res.user);
      setAuthStatus('authenticated');
      setSessionMessage(null);
      return res.user;
    }
    const me = await getCurrentUser();
    setUser(me);
    setAuthStatus('authenticated');
    setSessionMessage(null);
    return me;
  }, []);

  const register = useCallback(async ({ email, password, username }) => {
    // Backend contract: POST /auth/register returns the created user and
    // does NOT issue a JWT — the account must first be verified via the
    // emailed link, then the user signs in. Never persist a token here.
    const user = await registerWithCredentials({ email, password, username });
    return user;
  }, []);

  const refreshSession = useCallback(async () => {
    try {
      const res = await refreshToken();
      const rawToken = res?.access_token || res?.token;
      if (rawToken) {
        persistToken(rawToken);
        setTokenState(rawToken);
      }
    } catch {
      // Ignore refresh failures if unauthenticated
    }
  }, []);

  const logout = useCallback(() => {
    clearToken();
    apiClient.clearToken();
    setTokenState(null);
    setUser(null);
    setAuthStatus('unauthenticated');
    setSessionMessage(null);
  }, []);

  const clearSessionMessage = useCallback(() => setSessionMessage(null), []);

  const value = {
    user,
    token,
    isAuthenticated,
    loading,
    authStatus,
    sessionMessage,
    clearSessionMessage,
    completeOAuthLogin,
    login,
    register,
    refreshSession,
    logout,
    restoreSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
