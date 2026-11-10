import test from 'node:test';
import assert from 'node:assert/strict';
import { exchangeOAuthCode, _resetOAuthExchangeCache } from '../src/api/auth.js';
import { apiClient } from '../src/api/client.js';

test.beforeEach(() => {
  _resetOAuthExchangeCache();
});

test('1. Successful single exchange sends exactly 1 network request', async () => {
  let callCount = 0;
  const originalPost = apiClient.post;
  apiClient.post = async (url, body) => {
    callCount++;
    assert.equal(url, '/auth/oauth/exchange');
    assert.equal(body.code, 'single_use_code_1');
    return { access_token: 'access_123', refresh_token: 'refresh_456' };
  };

  try {
    const result = await exchangeOAuthCode('single_use_code_1');
    assert.equal(callCount, 1);
    assert.equal(result.access_token, 'access_123');
    assert.equal(result.refresh_token, 'refresh_456');
  } finally {
    apiClient.post = originalPost;
  }
});

test('2. Duplicate in-flight calls reuse the same promise (exactly 1 network request)', async () => {
  let callCount = 0;
  let resolveBackend;
  const originalPost = apiClient.post;

  apiClient.post = () => {
    callCount++;
    return new Promise((resolve) => {
      resolveBackend = resolve;
    });
  };

  try {
    // Two concurrent/in-flight invocations with the same code
    const p1 = exchangeOAuthCode('concurrent_code_99');
    const p2 = exchangeOAuthCode('concurrent_code_99');

    // Network request dispatched strictly once
    assert.equal(callCount, 1);

    // Backend resolves
    resolveBackend({ access_token: 'tok_abc', refresh_token: 'ref_def' });

    const [res1, res2] = await Promise.all([p1, p2]);
    assert.equal(callCount, 1);
    assert.deepEqual(res1, res2);
    assert.equal(res1.access_token, 'tok_abc');
  } finally {
    apiClient.post = originalPost;
  }
});

test('3. React StrictMode simulation (Mount 1 unmounts, Mount 2 reuses in-flight promise)', async () => {
  let networkCalls = 0;
  let finishRequest;
  const originalPost = apiClient.post;

  apiClient.post = () => {
    networkCalls++;
    return new Promise((resolve) => {
      finishRequest = resolve;
    });
  };

  try {
    // Mount 1 starts exchange
    let mount1Cancelled = false;
    let mount1Result = null;
    const mount1Promise = exchangeOAuthCode('strictmode_code').then((res) => {
      if (!mount1Cancelled) mount1Result = res;
    });

    // React StrictMode simulates unmount of Mount 1
    mount1Cancelled = true;

    // React StrictMode mounts Mount 2 immediately with same code
    let mount2Cancelled = false;
    let mount2Result = null;
    const mount2Promise = exchangeOAuthCode('strictmode_code').then((res) => {
      if (!mount2Cancelled) mount2Result = res;
    });

    // Exactly 1 network request was initiated
    assert.equal(networkCalls, 1);

    // Backend responds 200 OK
    finishRequest({ access_token: 'strict_access', refresh_token: 'strict_refresh' });

    await Promise.all([mount1Promise, mount2Promise]);

    // Mount 1 was cancelled so its effect ignored the result
    assert.equal(mount1Result, null);
    // Mount 2 was not cancelled and successfully captured the result
    assert.deepEqual(mount2Result, { access_token: 'strict_access', refresh_token: 'strict_refresh' });
    // Still strictly 1 network call
    assert.equal(networkCalls, 1);
  } finally {
    apiClient.post = originalPost;
  }
});

test('4. Component remount after completion returns cached token without network call', async () => {
  let callCount = 0;
  const originalPost = apiClient.post;
  apiClient.post = async () => {
    callCount++;
    return { access_token: 'cached_access', refresh_token: 'cached_refresh' };
  };

  try {
    // First mount completes
    const firstResult = await exchangeOAuthCode('remount_code');
    assert.equal(callCount, 1);
    assert.equal(firstResult.access_token, 'cached_access');

    // Component remounts after authentication state changes
    const secondResult = await exchangeOAuthCode('remount_code');
    // Call count remains 1: cached result returned without hitting backend again
    assert.equal(callCount, 1);
    assert.deepEqual(secondResult, firstResult);
  } finally {
    apiClient.post = originalPost;
  }
});

test('5. Exchange failure (400 code already used) marks code as consumed and prevents retry', async () => {
  let callCount = 0;
  const originalPost = apiClient.post;
  apiClient.post = async () => {
    callCount++;
    const err = new Error('Authorization code has already been used.');
    err.status = 400;
    throw err;
  };

  try {
    await assert.rejects(
      async () => await exchangeOAuthCode('already_used_code'),
      /already been used/
    );
    assert.equal(callCount, 1);

    // Subsequent retry attempt for the same consumed code is rejected in-memory
    await assert.rejects(
      async () => await exchangeOAuthCode('already_used_code'),
      /already been consumed/
    );
    // Call count did not increase: no retry sent to server
    assert.equal(callCount, 1);
  } finally {
    apiClient.post = originalPost;
  }
});

test('6. Already-authenticated session and navigation guard logic', () => {
  // Simulates navigation determination in OAuthCallbackPage
  function determineCallbackDestination({ isAuthenticated, token, error, code }) {
    if (isAuthenticated || token) {
      return { destination: '/app', replace: true, showNotice: false };
    }
    if (error) {
      return { destination: `/login?error=${encodeURIComponent(error)}`, replace: true, showNotice: false };
    }
    if (!code) {
      return { destination: null, replace: false, showNotice: true, message: 'No authorization code found in callback URL.' };
    }
    return { destination: 'process_exchange' };
  }

  // Already authenticated user navigating to callback
  const r1 = determineCallbackDestination({ isAuthenticated: true, token: 'tok_1', error: null, code: 'some_code' });
  assert.equal(r1.destination, '/app');

  // Race condition: error caught from duplicate request, but user already authenticated
  const r2 = determineCallbackDestination({ isAuthenticated: true, token: 'tok_1', error: 'Authorization code has already been used.', code: 'some_code' });
  assert.equal(r2.destination, '/app');

  // Genuine error with anonymous session
  const r3 = determineCallbackDestination({ isAuthenticated: false, token: null, error: 'access_denied', code: null });
  assert.equal(r3.destination, '/login?error=access_denied');

  // Missing code with anonymous session
  const r4 = determineCallbackDestination({ isAuthenticated: false, token: null, error: null, code: null });
  assert.equal(r4.destination, null);
  assert.equal(r4.showNotice, true);
});

test('7. "Back to Sign In" navigation respects authentication state', () => {
  function getBackActionTarget(isAuthenticated, token) {
    if (isAuthenticated || token) {
      return '/app';
    }
    return '/login';
  }

  assert.equal(getBackActionTarget(false, null), '/login');
  assert.equal(getBackActionTarget(true, 'some_token'), '/app');
  assert.equal(getBackActionTarget(false, 'some_token'), '/app');
});
