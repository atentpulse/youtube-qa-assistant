const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export const API_BASE_URL =
  typeof import.meta !== 'undefined' &&
  import.meta.env &&
  import.meta.env.VITE_API_BASE_URL !== undefined
    ? import.meta.env.VITE_API_BASE_URL
    : DEFAULT_API_BASE_URL;

export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this._token = null;
    this._onUnauthorized = null;
  }

  setToken(token) {
    this._token = token;
  }

  clearToken() {
    this._token = null;
  }

  getToken() {
    return this._token;
  }

  onUnauthorized(callback) {
    this._onUnauthorized = callback;
  }

  async request(endpoint, options = {}) {
    const {
      method = 'GET',
      headers = {},
      body,
      params,
      signal,
      timeout = 60000,
    } = options;

    let url = `${this.baseUrl}${endpoint}`;

    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) {
          searchParams.append(k, String(v));
        }
      });
      const qs = searchParams.toString();
      if (qs) {
        url += (url.includes('?') ? '&' : '?') + qs;
      }
    }

    const reqHeaders = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...headers,
    };

    if (this._token) {
      reqHeaders.Authorization = `Bearer ${this._token}`;
    }

    let controller;
    let timer;
    if (!signal) {
      controller = new AbortController();
      timer = setTimeout(() => controller.abort(), timeout);
    }

    const fetchOptions = {
      method,
      headers: reqHeaders,
      credentials: 'include',
      signal: signal || (controller ? controller.signal : undefined),
    };

    if (body !== undefined) {
      fetchOptions.body = typeof body === 'string' ? body : JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(url, fetchOptions);
    } catch (err) {
      if (timer) clearTimeout(timer);
      if (err.name === 'AbortError') {
        throw new ApiError('Request timed out. Please try again.', 408);
      }
      const rawMsg = err.message || '';
      const isFetchFailure =
        rawMsg.toLowerCase().includes('failed to fetch') ||
        rawMsg.toLowerCase().includes('load failed') ||
        rawMsg.toLowerCase().includes('networkerror');
      const errorMsg = isFetchFailure
        ? 'Unable to connect to the YtGenius server. Please verify the backend is running and reachable.'
        : (rawMsg || 'Network error. Please check your connection.');
      throw new ApiError(errorMsg, 0);
    } finally {
      if (timer) clearTimeout(timer);
    }

    let data = null;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      try {
        data = await response.json();
      } catch {
        // failed parse
      }
    } else {
      try {
        data = await response.text();
      } catch {
        // ignore
      }
    }

    if (!response.ok) {
      if (response.status === 401) {
        if (typeof this._onUnauthorized === 'function') {
          this._onUnauthorized();
        }
        // AuthContext listens for this window event to clear auth state.
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      }
      const message =
        (data && (data.detail || data.message || data.error)) ||
        `Request failed with status ${response.status}`;
      throw new ApiError(message, response.status, data);
    }

    return data;
  }

  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  post(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'POST', body });
  }

  put(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'PUT', body });
  }

  patch(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'PATCH', body });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
export default apiClient;
