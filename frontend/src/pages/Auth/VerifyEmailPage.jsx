import React, { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, XCircle } from 'lucide-react';
import { verifyEmail } from '../../api/auth';
import Spinner from '../../components/common/Spinner';
import styles from '../AuthPages.module.css';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  // Status: 'idle' | 'loading' | 'success' | 'error'
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const executedRef = useRef(false);

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('No verification token provided. Please check the link in your email.');
      return;
    }

    if (executedRef.current) return;
    executedRef.current = true;

    setStatus('loading');
    verifyEmail(token)
      .then((data) => {
        setStatus('success');
        setMessage(data?.message || 'Your email has been verified successfully.');
      })
      .catch((err) => {
        setStatus('error');
        const detail = err?.data?.detail || err?.message || 'Verification link is invalid or has expired.';
        setMessage(detail);
      });
  }, [token]);

  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <Link to="/" className={styles.brandLink}>
          <div className={styles.brandIcon}>▶</div>
          <span className={styles.brandName}>
            <span className={styles.brandYt}>Yt</span>
            <span className={styles.brandGenius}>Genius</span>
          </span>
        </Link>

        <h1 className={styles.title}>Email Verification</h1>

        {status === 'loading' && (
          <div className={styles.callbackStatus} data-testid="verify-loading">
            <Spinner size={24} />
            <p className={styles.body}>Verifying your email address…</p>
          </div>
        )}

        {status === 'success' && (
          <div data-testid="verify-success">
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
              <CheckCircle2 size={44} color="#22c55e" />
            </div>
            <p className={styles.successNotice}>{message}</p>
            <p className={styles.body}>You can now sign in to your YtGenius account.</p>
            <Link to="/login" className={styles.primaryButton} data-testid="verify-login-button">
              Continue to Sign In
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div data-testid="verify-error">
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
              <XCircle size={44} color="#ef4444" />
            </div>
            <p className={styles.errorNotice}>{message}</p>
            <p className={styles.body}>
              If this link has expired, you can request a new verification email from the sign-in page.
            </p>
            <Link to="/login" className={styles.secondaryButton}>
              Back to Sign In
            </Link>
          </div>
        )}
      </div>

      <Link to="/" className={styles.backHomeLink}>
        <ArrowLeft size={14} /> Back to homepage
      </Link>
    </div>
  );
}
