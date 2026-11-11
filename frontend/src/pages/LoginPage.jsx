import React, { useEffect, useState } from 'react';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../api/client';
import { sendLoginOtp, verifyLoginOtp } from '../api/auth';
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

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const { isAuthenticated, loading, sessionMessage, clearSessionMessage, completeOAuthLogin } = useAuth();
  const [searchParams] = useSearchParams();
  const oauthError = searchParams.get('error');

  const [isRedirectingGoogle, setIsRedirectingGoogle] = useState(false);
  const [step, setStep] = useState('email'); // 'email' | 'otp'
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => () => clearSessionMessage(), [clearSessionMessage]);

  // Resend cooldown timer
  useEffect(() => {
    if (step !== 'otp' || cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [step, cooldown]);

  if (loading) {
    return (
      <div className={styles.wrap}>
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
    setIsRedirectingGoogle(true);
    window.location.href = `${API_BASE_URL}/auth/google/login`;
  };

  const handleContinueWithEmail = async (e) => {
    e.preventDefault();
    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setErrorMessage('Please enter your email address.');
      return;
    }
    if (!EMAIL_REGEX.test(cleanEmail)) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    setIsSendingEmail(true);
    setErrorMessage(null);

    try {
      const res = await sendLoginOtp(cleanEmail);
      setCooldown(res?.cooldown_seconds || 60);
      setStep('otp');
      setOtp('');
    } catch (err) {
      setErrorMessage(err?.message || 'Failed to send login code. Please try again.');
    } finally {
      setIsSendingEmail(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e?.preventDefault();
    const cleanOtp = otp.trim();
    if (cleanOtp.length !== 6) {
      setErrorMessage('Please enter the 6-digit code sent to your email.');
      return;
    }

    setIsVerifying(true);
    setErrorMessage(null);

    try {
      const data = await verifyLoginOtp({ email: email.trim(), otp: cleanOtp });
      const accessToken = data?.access_token || data?.token;
      const refreshToken = data?.refresh_token;

      if (!accessToken) {
        throw new Error('No access token returned from server.');
      }

      await completeOAuthLogin(accessToken, refreshToken);
    } catch (err) {
      setErrorMessage(err?.message || 'Invalid or expired code. Please try again.');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResendOtp = async () => {
    if (cooldown > 0 || isResending) return;
    setIsResending(true);
    setErrorMessage(null);

    try {
      const res = await sendLoginOtp(email.trim());
      setCooldown(res?.cooldown_seconds || 60);
      setOtp('');
    } catch (err) {
      setErrorMessage(err?.message || 'Failed to resend code. Please wait and try again.');
    } finally {
      setIsResending(false);
    }
  };

  const handleChangeEmail = () => {
    setStep('email');
    setOtp('');
    setErrorMessage(null);
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <Link to="/" className={styles.brandLink}>
          <div className={styles.brandIcon}>▶</div>
          <span className={styles.brandName}>
            <span className={styles.brandYt}>Yt</span><span className={styles.brandGenius}>Genius</span>
          </span>
        </Link>

        {sessionMessage && <p className={styles.notice}>{sessionMessage}</p>}
        {oauthError && (
          <p className={styles.errorNotice} data-testid="auth-error-notice">
            {oauthError}
          </p>
        )}
        {errorMessage && (
          <p className={styles.errorNotice} data-testid="auth-error-message">
            {errorMessage}
          </p>
        )}

        {step === 'email' ? (
          <div data-testid="email-step">
            <h1 className={styles.title}>Welcome to YtGenius</h1>
            <p className={styles.body}>Ask questions about any YouTube video with AI.</p>

            <button
              type="button"
              className={styles.googleButton}
              onClick={handleContinueWithGoogle}
              disabled={isRedirectingGoogle || isSendingEmail}
              aria-label="Continue with Google"
              data-testid="google-auth-button"
            >
              {isRedirectingGoogle ? (
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

            <div className={styles.divider}>
              <div className={styles.dividerLine} />
              <span className={styles.dividerText}>OR</span>
              <div className={styles.dividerLine} />
            </div>

            <form onSubmit={handleContinueWithEmail} data-testid="email-form">
              <input
                type="email"
                required
                autoFocus
                placeholder="Enter your email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (errorMessage) setErrorMessage(null);
                }}
                disabled={isSendingEmail}
                className={styles.emailInput}
                data-testid="email-input"
              />

              <button
                type="submit"
                disabled={isSendingEmail || !email.trim()}
                className={styles.continueEmailButton}
                data-testid="continue-email-button"
              >
                {isSendingEmail ? (
                  <>
                    <Spinner size={16} />
                    <span>Sending code…</span>
                  </>
                ) : (
                  'Continue with email'
                )}
              </button>
            </form>
          </div>
        ) : (
          <div data-testid="otp-step">
            <h1 className={styles.title}>Check your email</h1>
            <p className={styles.body}>
              We sent a 6-digit code to <span className={styles.emailDisplay}>{email}</span>
            </p>

            <form onSubmit={handleVerifyOtp} data-testid="otp-form">
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                required
                autoFocus
                placeholder="••••••"
                value={otp}
                onChange={(e) => {
                  const val = e.target.value.replace(/\D/g, '').slice(0, 6);
                  setOtp(val);
                  if (errorMessage) setErrorMessage(null);
                }}
                disabled={isVerifying}
                className={styles.otpInput}
                data-testid="otp-input"
              />

              <button
                type="submit"
                disabled={isVerifying || otp.trim().length !== 6}
                className={styles.primaryButton}
                style={{ marginTop: '14px' }}
                data-testid="verify-otp-button"
              >
                {isVerifying ? (
                  <>
                    <Spinner size={16} />
                    <span>Verifying…</span>
                  </>
                ) : (
                  'Verify and continue'
                )}
              </button>
            </form>

            <div className={styles.otpActions}>
              {cooldown > 0 ? (
                <span className={styles.resendText} data-testid="resend-countdown">
                  Resend code in {cooldown}s
                </span>
              ) : (
                <button
                  type="button"
                  onClick={handleResendOtp}
                  disabled={isResending}
                  className={styles.resendLink}
                  data-testid="resend-button"
                >
                  {isResending ? 'Sending code…' : 'Resend code'}
                </button>
              )}

              <button
                type="button"
                onClick={handleChangeEmail}
                className={styles.changeEmailButton}
                data-testid="change-email-button"
              >
                Use a different email
              </button>
            </div>
          </div>
        )}
      </div>

      <Link to="/" className={styles.backHomeLink}>
        <ArrowLeft size={14} /> Back to homepage
      </Link>
    </div>
  );
}
