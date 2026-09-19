import React, { useEffect, useState } from 'react';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../api/client';
import Spinner from '../components/common/Spinner';
import styles from './AuthPages.module.css';

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.87 2.7-6.62z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.9v2.33A9 9 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.16.28-1.7V4.97H.9A9 9 0 0 0 0 9c0 1.45.35 2.83.9 4.03l3.05-2.33z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .9 4.97l3.05 2.33C4.66 5.17 6.65 3.58 9 3.58z"
      />
    </svg>
  );
}

// VidMind uses Google as the ONLY sign-in method. This page presents a single
// "Continue with Google" action that redirects to the existing backend OAuth
// endpoint (GET /api/auth/google/login). No email/password UI is shown.
export default function LoginPage() {
  const { isAuthenticated, loading, sessionMessage, clearSessionMessage } = useAuth();
  const [searchParams] = useSearchParams();
  const oauthError = searchParams.get('error');
  const [isRedirecting, setIsRedirecting] = useState(false);

  useEffect(() => () => clearSessionMessage(), [clearSessionMessage]);

  if (loading) {
    return (
      <div className={`${styles.wrap} force-light-theme`}>
        <div className={styles.card}>
          <div className={styles.callbackStatus}>
            <Spinner size={24} />
            <span>Checking session…</span>
          </div>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/app" replace />;
  }

  const handleContinueWithGoogle = () => {
    setIsRedirecting(true);
    window.location.href = `${API_BASE_URL}/auth/google/login`;
  };

  return (
    <div className={`${styles.wrap} force-light-theme`}>
      <div className={styles.card}>
        <Link to="/" className={styles.brandLink}>
          <img src="/logo.svg" alt="VidMind logo" className={styles.brandLogoImg} />
          <span className={styles.brandName}>
            VidMind<span className={styles.brandAccent}>.</span>
          </span>
        </Link>

        <h1 className={styles.title}>Welcome to VidMind</h1>
        <p className={styles.body}>Ask questions about any YouTube video with AI.</p>

        {sessionMessage && <p className={styles.notice}>{sessionMessage}</p>}
        {oauthError && (
          <p className={styles.errorNotice} data-testid="auth-error-notice">
            {oauthError}
          </p>
        )}

        <button
          type="button"
          className={styles.googleButton}
          onClick={handleContinueWithGoogle}
          disabled={isRedirecting}
          aria-label="Continue with Google"
          data-testid="google-auth-button"
        >
          {isRedirecting ? (
            <>
              <Spinner size={16} />
              <span>Redirecting to Google…</span>
            </>
          ) : (
            <>
              <GoogleIcon />
              <span>Continue with Google</span>
            </>
          )}
        </button>

        <p className={styles.supportingText}>Sign in securely with your Google account.</p>

        <div className={styles.authInfoNotice}>
          The same Google sign-in works for new and returning users. VidMind accesses only your
          verified basic profile to identify your video library.
        </div>
      </div>

      <Link to="/" className={styles.backHomeLink}>
        <ArrowLeft size={14} /> Back to homepage
      </Link>
    </div>
  );
}
