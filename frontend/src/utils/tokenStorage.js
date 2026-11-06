const TOKEN_KEY = 'ytgenius_auth_token';
const REFRESH_TOKEN_KEY = 'ytgenius_refresh_token';
const LEGACY_TOKEN_KEY = 'reel_auth_token';

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || localStorage.getItem(LEGACY_TOKEN_KEY);
  } catch (e) {
    return null;
  }
}

export function getRefreshToken() {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch (e) {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(LEGACY_TOKEN_KEY);
    }
  } catch (e) {
    // ignore
  }
}

export function setRefreshToken(refreshToken) {
  try {
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    } else {
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  } catch (e) {
    // ignore
  }
}

export function setAuthTokens({ accessToken, refreshToken }) {
  setToken(accessToken);
  if (refreshToken) {
    setRefreshToken(refreshToken);
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(LEGACY_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch (e) {
    // ignore
  }
}
