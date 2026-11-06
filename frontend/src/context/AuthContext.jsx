import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getCurrentUser, loginWithCredentials, registerWithCredentials, refreshToken } from '../api/auth';
import { apiClient } from '../api/client';
import {
  getToken,
  getRefreshToken,
  setToken as persistToken,
  setRefreshToken as persistRefreshToken,
  clearToken,
} from '../utils/tokenStorage';

const AuthContext = createContext(null);

// 'initializing' — startup restoreSession() hasn't resolved yet.
// 'authenticated' — valid token + user loaded.
// 'unauthenticated' — no token, or the token was rejected/cleared.
//
// YtGenius exclusively supports Google OAuth authentication. Sessions
// persist with a 60-minute access token and a 7-day refresh token.
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
    const storedRefreshToken = getRefreshToken();

    if (!storedToken && !storedRefreshToken) {
      setAuthStatus('unauthenticated');
      return;
    }

    if (storedToken) {
      setTokenState(storedToken);
      apiClient.setToken(storedToken);

      try {
        const me = await getCurrentUser();
        setUser(me);
        setAuthStatus('authenticated');
        return;
      } catch {
        // Access token expired or invalid; attempt automatic refresh below
      }
    }

    // Attempt automatic refresh if refresh token is present
    if (storedRefreshToken) {
      try {
        const res = await refreshToken({ refresh_token: storedRefreshToken });
        const newAccess = res?.access_token || res?.token;
        const newRefresh = res?.refresh_token;
        if (newAccess) {
          persistToken(newAccess);
          if (newRefresh) {
            persistRefreshToken(newRefresh);
          }
          setTokenState(newAccess);
          apiClient.setToken(newAccess);

          const me = await getCurrentUser();
          setUser(me);
          setAuthStatus('authenticated');
          return;
        }
      } catch {
        // Refresh token invalid or expired
      }
    }

    // If both access token and refresh attempt failed
    clearToken();
    setTokenState(null);
    setUser(null);
    setAuthStatus('unauthenticated');
  }, []);

  // Restore session once on startup.
  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  // A 401 from ANY request: try token refresh before ending session
  useEffect(() => {
    const onUnauthorized = async () => {
      const storedRefreshToken = getRefreshToken();
      if (storedRefreshToken) {
        try {
          const res = await refreshToken({ refresh_token: storedRefreshToken });
          const newAccess = res?.access_token || res?.token;
          const newRefresh = res?.refresh_token;
          if (newAccess) {
            persistToken(newAccess);
            if (newRefresh) persistRefreshToken(newRefresh);
            setTokenState(newAccess);
            apiClient.setToken(newAccess);
            const me = await getCurrentUser();
            setUser(me);
            setAuthStatus('authenticated');
            return;
          }
        } catch {
          // Refresh failed
        }
      }
      clearToken();
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
   * /oauth/callback?token=<jwt>&refresh_token=<jwt>. This stores both tokens
   * through centralized tokenStorage, then restores the user via GET /auth/me.
   */
  const completeOAuthLogin = useCallback(async (rawToken, rawRefreshToken = null) => {
    persistToken(rawToken);
    if (rawRefreshToken) {
      persistRefreshToken(rawRefreshToken);
    }
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
      const storedRefreshToken = getRefreshToken();
      const res = await refreshToken(storedRefreshToken ? { refresh_token: storedRefreshToken } : {});
      const rawToken = res?.access_token || res?.token;
      const rawRefresh = res?.refresh_token;
      if (rawToken) {
        persistToken(rawToken);
        if (rawRefresh) {
          persistRefreshToken(rawRefresh);
        }
        setTokenState(rawToken);
        apiClient.setToken(rawToken);
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
