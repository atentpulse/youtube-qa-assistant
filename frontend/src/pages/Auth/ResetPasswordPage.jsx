import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, Lock } from 'lucide-react';
import { resetPassword } from '../../api/auth';
import Spinner from '../../components/common/Spinner';
import styles from '../AuthPages.module.css';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(token ? '' : 'No reset token provided. Please request a new password reset link.');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!token) {
      setError('Missing or invalid reset token. Please request a new password reset link.');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setError('');
    setIsSubmitting(true);

    try {
      await resetPassword({ token, new_password: password });
      setIsSuccess(true);
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 3000);
    } catch (err) {
      const detail = err?.data?.detail || err?.message || 'Password reset failed. The link may have expired.';
      setError(detail);
    } finally {
      setIsSubmitting(false);
    }
  };

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

        <h1 className={styles.title}>Reset Your Password</h1>
        <p className={styles.body}>Choose a new secure password for your account.</p>

        {isSuccess ? (
          <div data-testid="reset-success">
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
              <CheckCircle2 size={44} color="#22c55e" />
            </div>
            <p className={styles.successNotice}>Your password has been reset successfully.</p>
            <p className={styles.body}>Redirecting to sign in…</p>
            <Link to="/login" className={styles.primaryButton}>
              Sign In Now
            </Link>
          </div>
        ) : (
          <>
            {error && <p className={styles.errorNotice} data-testid="reset-error">{error}</p>}

            {token && (
              <form onSubmit={handleSubmit} className={styles.form}>
                <div className={styles.formGroup}>
                  <label htmlFor="new-password" className={styles.label}>
                    New Password
                  </label>
                  <input
                    id="new-password"
                    type="password"
                    className={styles.input}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter at least 6 characters"
                    disabled={isSubmitting}
                    required
                    autoComplete="new-password"
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="confirm-password" className={styles.label}>
                    Confirm New Password
                  </label>
                  <input
                    id="confirm-password"
                    type="password"
                    className={styles.input}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter your new password"
                    disabled={isSubmitting}
                    required
                    autoComplete="new-password"
                  />
                </div>

                <button
                  type="submit"
                  className={styles.primaryButton}
                  disabled={isSubmitting || !password || !confirmPassword}
                  data-testid="reset-submit-button"
                >
                  {isSubmitting ? (
                    <>
                      <Spinner size={16} />
                      <span>Updating password…</span>
                    </>
                  ) : (
                    <>
                      <Lock size={15} />
                      <span>Reset Password</span>
                    </>
                  )}
                </button>
              </form>
            )}

            {!token && (
              <Link to="/login" className={styles.secondaryButton}>
                Back to Sign In
              </Link>
            )}
          </>
        )}
      </div>

      <Link to="/" className={styles.backHomeLink}>
        <ArrowLeft size={14} /> Back to homepage
      </Link>
    </div>
  );
}
