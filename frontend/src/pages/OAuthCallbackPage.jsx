import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Spinner from '../components/common/Spinner';
import styles from './AuthPages.module.css';

export default function OAuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { completeOAuthLogin } = useAuth();
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function handleCallback() {
      const error = searchParams.get('error');
      if (error) {
        if (!cancelled) {
          navigate(`/login?error=${encodeURIComponent(error)}`, { replace: true });
        }
        return;
      }

      const token = searchParams.get('token');
      if (!token) {
        if (!cancelled) {
          setErrorMessage('No authentication token found in callback URL.');
        }
        return;
      }

      try {
        await completeOAuthLogin(token);
        if (!cancelled) {
          navigate('/app', { replace: true });
        }
      } catch (err) {
        if (!cancelled) {
          setErrorMessage(
            err?.message || 'Failed to complete sign in. Please try again.'
          );
        }
      }
    }

    handleCallback();

    return () => {
      cancelled = true;
    };
  }, [searchParams, completeOAuthLogin, navigate]);

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
            onClick={() => navigate('/login', { replace: true })}
          >
            Back to Sign In
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
            Verifying your Google authentication token...
          </p>
        </div>
      </div>
    </div>
  );
}
