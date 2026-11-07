import React from 'react';
import { useAuth } from '../../../context/AuthContext';
import { Shield, Lock, Check, LogOut, Laptop, AlertCircle } from 'lucide-react';
import common from './CategoryCommon.module.css';

export default function SecurityCategory({ onTriggerLogout, onNavigateCategory }) {
  const { user } = useAuth();
  const isGoogle = user?.auth_provider === 'google';

  return (
    <div className={common.container}>
      <div className={common.header}>
        <h2 className={common.title}>Security &amp; Authentication</h2>
        <p className={common.description}>
          Review authentication mechanisms, token security, and session management.
        </p>
      </div>

      {/* Auth Provider & Identity */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Authentication Method</h3>
          <p className={common.sectionSubtitle}>
            How your identity is verified on YtGenius.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Primary Authentication Provider</span>
            <span className={common.rowDescription}>
              {isGoogle
                ? 'Your account is authenticated via Google OAuth 2.0 single sign-on.'
                : 'Your account is secured with email and password credentials.'}
            </span>
          </div>
          <span className={`${common.badge} ${common.badgeBlue}`}>
            <Shield size={12} /> {isGoogle ? 'Google OAuth 2.0' : 'Email & Password'}
          </span>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Password Management</span>
            <span className={common.rowDescription}>
              {isGoogle
                ? 'Password changes are managed through your Google Account security portal.'
                : 'Account password configured and hashed using bcrypt.'}
            </span>
          </div>
          <span className={`${common.badge} ${common.badgeNeutral}`}>
            <Lock size={12} /> {isGoogle ? 'Managed by Google' : 'Configured'}
          </span>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Email Verification Status</span>
            <span className={common.rowDescription}>
              Verified emails ensure secure password recovery and account ownership.
            </span>
          </div>
          {user?.email_verified ? (
            <span className={`${common.badge} ${common.badgeSuccess}`}>
              <Check size={12} /> Verified
            </span>
          ) : (
            <span className={`${common.badge} ${common.badgeWarning}`}>
              <AlertCircle size={12} /> Pending Verification
            </span>
          )}
        </div>
      </div>

      {/* Session Security (Stateless JWT Architecture) */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Session Architecture</h3>
          <p className={common.sectionSubtitle}>
            Stateless JSON Web Token (JWT) session configuration.
          </p>
        </div>

        <div className={common.noticeBox}>
          <Laptop size={18} className={common.noticeIcon} />
          <div>
            <strong style={{ color: '#ffffff', display: 'block', marginBottom: '2px' }}>
              Stateless JWT Token Lifecycle
            </strong>
            <span>
              YtGenius issues cryptographically signed HMAC-SHA256 tokens. Tokens expire after 24 hours. Log out invalidates the token on this device. Remote multi-device session revocation is not supported in the stateless JWT configuration.
            </span>
          </div>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Current Browser Session</span>
            <span className={common.rowDescription}>
              Active session in this browser window. Token is stored securely in local browser storage.
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className={`${common.badge} ${common.badgeSuccess}`}>
              <Check size={11} /> Active
            </span>
            <button
              type="button"
              className={common.btnSecondary}
              onClick={onTriggerLogout}
              data-testid="security-signout-session-btn"
            >
              <LogOut size={13} /> Log Out This Device
            </button>
          </div>
        </div>
      </div>

      {/* Account Deletion Entry Point */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Account Lifecycle</h3>
          <p className={common.sectionSubtitle}>
            Permanent closure and data erasure options.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Account Deletion</span>
            <span className={common.rowDescription}>
              Delete your account and unlink all saved videos via the Data &amp; Privacy portal.
            </span>
          </div>
          <button
            type="button"
            className={common.btnDanger}
            onClick={() => onNavigateCategory('data')}
            data-testid="security-goto-data-btn"
          >
            Manage in Data &amp; Privacy →
          </button>
        </div>
      </div>
    </div>
  );
}
