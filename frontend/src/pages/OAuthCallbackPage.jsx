import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getToken } from '../utils/tokenStorage';
import Spinner from '../components/common/Spinner';
import styles from './AuthPages.module.css';

// Module-level tracking to coordinate across React StrictMode remounts
let lastHandledCode = null;

export default function OAuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { isAuthenticated, loginWithOAuthCode } = useAuth();
  const [errorMessage, setErrorMessage] = useState(null);

  // Capture code and error query parameters
  const rawCode = searchParams.get('code');
  const rawError = searchParams.get('error');

  if (rawCode) {
    lastHandledCode = rawCode;
  }

  const codeRef = useRef(rawCode || lastHandledCode);
  const errorRef = useRef(rawError);
  const isStartedRef = useRef(false);

  // Requirement 6: Remove the authorization code from browser history immediately after capturing it
  useEffect(() => {
    if (searchParams.has('code') || searchParams.has('error')) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [searchParams]);

  useEffect(() => {
    // 1. If already authenticated, redirect straight to app workspace
    if (isAuthenticated) {
      navigate('/app', { replace: true });
      return;
    }

    // 2. If Google returned an error query parameter
    const oauthError = errorRef.current;
    if (oauthError) {
      navigate(`/login?error=${encodeURIComponent(oauthError)}`, { replace: true });
      return;
    }

    // 3. Check for authorization code
    const code = codeRef.current;
    if (!code) {
      setErrorMessage('No authorization code found in callback URL.');
      return;
    }

    // 4. Concurrency Guard: Only initiate processing once per component instance
    if (isStartedRef.current) {
      return;
    }
    isStartedRef.current = true;

    let isMounted = true;

    async function processCallback() {
      try {
        await loginWithOAuthCode(code);
        if (isMounted) {
          navigate('/app', { replace: true });
        }
      } catch (err) {
        // Requirement 8: Do not treat an already-authenticated session as a failure
        // merely because a duplicate/concurrent request was rejected.
        if (isAuthenticated || getToken()) {
          if (isMounted) {
            navigate('/app', { replace: true });
          }
          return;
        }

        if (isMounted) {
          setErrorMessage(
            err?.message || 'Failed to complete sign in. Please try again.'
          );
        }
      }
    }

    processCallback();

    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, loginWithOAuthCode, navigate]);

  const handleBackAction = () => {
    if (isAuthenticated || getToken()) {
      navigate('/app', { replace: true });
    } else {
      navigate('/login', { replace: true });
    }
  };

  if (errorMessage) {
    return (
      <div className={styles.wrap}>
        <div className={styles.card}>
          <Link to="/" className={styles.brandLink}>
            <div className={styles.brandIcon}>▶</div>
            <span className={styles.brandName}>
              <span className={styles.brandYt}>Yt</span><span className={styles.brandGenius}>Genius</span>
            </span>
          </Link>

          <h1 className={styles.title}>Sign in error</h1>
          <p className={styles.errorNotice}>{errorMessage}</p>
          <button
            type="button"
            className={styles.submitButton}
            onClick={handleBackAction}
          >
            {isAuthenticated || getToken() ? 'Go to Workspace' : 'Back to Sign In'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <Link to="/" className={styles.brandLink}>
          <div className={styles.brandIcon}>▶</div>
          <span className={styles.brandName}>
            <span className={styles.brandYt}>Yt</span><span className={styles.brandGenius}>Genius</span>
          </span>
        </Link>

        <div className={styles.callbackStatus}>
          <Spinner size={32} />
          <p className={styles.title} style={{ fontSize: '16px', marginBottom: 2 }}>
            Completing sign in…
          </p>
          <p className={styles.supportingText} style={{ marginTop: 0 }}>
            Verifying your Google authorization code...
          </p>
        </div>
      </div>
    </div>
  );
}
