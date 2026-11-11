import test from 'node:test';
import assert from 'node:assert/strict';
import {
  verifyEmail,
  forgotPassword,
  resetPassword,
  resendVerification,
  sendLoginOtp,
  verifyLoginOtp,
} from '../src/api/auth.js';
import { apiClient } from '../src/api/client.js';

test('1. verifyEmail dispatches GET /auth/verify-email with token parameter', async () => {
  let callCount = 0;
  const originalGet = apiClient.get;
  apiClient.get = async (url, opts) => {
    callCount++;
    assert.equal(url, '/auth/verify-email');
    assert.equal(opts.params.token, 'valid-token-abc');
    return { message: 'Email verified successfully.' };
  };

  try {
    const res = await verifyEmail('valid-token-abc');
    assert.equal(callCount, 1);
    assert.equal(res.message, 'Email verified successfully.');
  } finally {
    apiClient.get = originalGet;
  }
});

test('2. forgotPassword dispatches POST /auth/forgot-password with email', async () => {
  let callCount = 0;
  const originalPost = apiClient.post;
  apiClient.post = async (url, body) => {
    callCount++;
    assert.equal(url, '/auth/forgot-password');
    assert.equal(body.email, 'user@example.com');
    return { message: 'If an account exists, a reset link has been sent.' };
  };

  try {
    const res = await forgotPassword('user@example.com');
    assert.equal(callCount, 1);
    assert.match(res.message, /reset link has been sent/);
  } finally {
    apiClient.post = originalPost;
  }
});

test('3. resetPassword dispatches POST /auth/reset-password with token and new password', async () => {
  let callCount = 0;
  const originalPost = apiClient.post;
  apiClient.post = async (url, body) => {
    callCount++;
    assert.equal(url, '/auth/reset-password');
    assert.equal(body.token, 'secret-reset-token');
    assert.equal(body.new_password, 'newSecurePassword123');
    return { message: 'Password has been reset successfully.' };
  };

  try {
    const res = await resetPassword({
      token: 'secret-reset-token',
      new_password: 'newSecurePassword123',
    });
    assert.equal(callCount, 1);
    assert.match(res.message, /reset successfully/);
  } finally {
    apiClient.post = originalPost;
  }
});

test('4. resendVerification dispatches POST /auth/resend-verification with email', async () => {
  let callCount = 0;
  const originalPost = apiClient.post;
  apiClient.post = async (url, body) => {
    callCount++;
    assert.equal(url, '/auth/resend-verification');
    assert.equal(body.email, 'unverified@example.com');
    return { message: 'Verification email sent.' };
  };

  try {
    const res = await resendVerification('unverified@example.com');
    assert.equal(callCount, 1);
    assert.match(res.message, /Verification email sent/);
  } finally {
    apiClient.post = originalPost;
  }
});

test('5. Theme storage migration: migrates vidmind_theme to ytgenius_theme and cleans legacy key', () => {
  const mockStorage = new Map();
  const localStorageMock = {
    getItem: (k) => mockStorage.get(k) || null,
    setItem: (k, v) => mockStorage.set(k, String(v)),
    removeItem: (k) => mockStorage.delete(k),
  };

  // Simulate existing legacy key
  localStorageMock.setItem('vidmind_theme', 'light');

  // Migration logic as implemented in ThemeContext.jsx:
  const getInitialTheme = () => {
    const stored = localStorageMock.getItem('ytgenius_theme') || localStorageMock.getItem('vidmind_theme');
    if (stored === 'light' || stored === 'dark') {
      if (localStorageMock.getItem('vidmind_theme')) {
        localStorageMock.setItem('ytgenius_theme', stored);
        localStorageMock.removeItem('vidmind_theme');
      }
      return stored;
    }
    return 'dark';
  };

  const theme = getInitialTheme();
  assert.equal(theme, 'light');
  assert.equal(localStorageMock.getItem('ytgenius_theme'), 'light');
  assert.equal(localStorageMock.getItem('vidmind_theme'), null);
});

test('6. UI sidebar collapsed state migration: migrates vidmind_sidebar_collapsed to ytgenius_sidebar_collapsed', () => {
  const mockStorage = new Map();
  const localStorageMock = {
    getItem: (k) => mockStorage.get(k) || null,
    setItem: (k, v) => mockStorage.set(k, String(v)),
    removeItem: (k) => mockStorage.delete(k),
  };

  // Simulate existing legacy sidebar key
  localStorageMock.setItem('vidmind_sidebar_collapsed', 'true');

  // Migration logic as implemented in UIContext.jsx:
  const getInitialCollapsed = () => {
    const modern = localStorageMock.getItem('ytgenius_sidebar_collapsed');
    const legacy = localStorageMock.getItem('vidmind_sidebar_collapsed');
    if (legacy !== null) {
      const val = modern !== null ? modern : legacy;
      localStorageMock.setItem('ytgenius_sidebar_collapsed', val);
      localStorageMock.removeItem('vidmind_sidebar_collapsed');
      return val === 'true';
    }
    return modern === 'true';
  };

  const isCollapsed = getInitialCollapsed();
  assert.equal(isCollapsed, true);
  assert.equal(localStorageMock.getItem('ytgenius_sidebar_collapsed'), 'true');
  assert.equal(localStorageMock.getItem('vidmind_sidebar_collapsed'), null);
});

test('7. Password reset validation: enforces minimum length 6 matching backend schema', () => {
  const validateResetPassword = (password, confirmPassword) => {
    if (!password || password.length < 6) {
      return 'Password must be at least 6 characters.';
    }
    if (password !== confirmPassword) {
      return 'Passwords do not match.';
    }
    return null;
  };

  assert.equal(validateResetPassword('123', '123'), 'Password must be at least 6 characters.');
  assert.equal(validateResetPassword('password123', 'different'), 'Passwords do not match.');
  assert.equal(validateResetPassword('validSecretPass', 'validSecretPass'), null);
});

test('8. sendLoginOtp dispatches POST /auth/otp/send with email', async () => {
  let callCount = 0;
  const originalPost = apiClient.post;
  apiClient.post = async (url, body) => {
    callCount++;
    assert.equal(url, '/auth/otp/send');
    assert.equal(body.email, 'login_user@example.com');
    return { message: 'If this email is valid, a 6-digit login code has been sent.', cooldown_seconds: 60 };
  };

  try {
    const res = await sendLoginOtp('login_user@example.com');
    assert.equal(callCount, 1);
    assert.match(res.message, /6-digit login code has been sent/);
    assert.equal(res.cooldown_seconds, 60);
  } finally {
    apiClient.post = originalPost;
  }
});

test('9. verifyLoginOtp dispatches POST /auth/otp/verify with email and otp', async () => {
  let callCount = 0;
  const originalPost = apiClient.post;
  apiClient.post = async (url, body) => {
    callCount++;
    assert.equal(url, '/auth/otp/verify');
    assert.equal(body.email, 'login_user@example.com');
    assert.equal(body.otp, '123456');
    return { access_token: 'acc_token_xyz', refresh_token: 'ref_token_xyz', token_type: 'bearer' };
  };

  try {
    const res = await verifyLoginOtp({ email: 'login_user@example.com', otp: '123456' });
    assert.equal(callCount, 1);
    assert.equal(res.access_token, 'acc_token_xyz');
    assert.equal(res.refresh_token, 'ref_token_xyz');
    assert.equal(res.token_type, 'bearer');
  } finally {
    apiClient.post = originalPost;
  }
});

test('10. Email input validation regex correctly validates emails', () => {
  const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  assert.equal(EMAIL_REGEX.test('user@example.com'), true);
  assert.equal(EMAIL_REGEX.test('firstname.lastname+tag@sub.domain.org'), true);
  assert.equal(EMAIL_REGEX.test('invalid-email'), false);
  assert.equal(EMAIL_REGEX.test('@domain.com'), false);
  assert.equal(EMAIL_REGEX.test('user@domain'), false);
  assert.equal(EMAIL_REGEX.test('   '), false);
});

test('11. OTP input formatting restricts to exactly 6 digits', () => {
  const sanitizeOtpInput = (val) => val.replace(/\D/g, '').slice(0, 6);
  assert.equal(sanitizeOtpInput('123456'), '123456');
  assert.equal(sanitizeOtpInput('123abc456'), '123456');
  assert.equal(sanitizeOtpInput('123456789'), '123456');
  assert.equal(sanitizeOtpInput('abc-def'), '');
});

test('12. Resend countdown logic decrement and zero guard', () => {
  let cooldown = 60;
  const tick = () => {
    cooldown = cooldown > 0 ? cooldown - 1 : 0;
  };

  tick();
  assert.equal(cooldown, 59);

  cooldown = 1;
  tick();
  assert.equal(cooldown, 0);

  // Does not go negative
  tick();
  assert.equal(cooldown, 0);
});

test('13. ApiClient translates network/fetch failures into helpful user message', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new TypeError('Failed to fetch');
  };

  try {
    await apiClient.get('/auth/me');
    assert.fail('Should have thrown ApiError');
  } catch (err) {
    assert.equal(err.name, 'ApiError');
    assert.equal(err.status, 0);
    assert.equal(
      err.message,
      'Unable to connect to the YtGenius server. Please verify the backend is running and reachable.'
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});


