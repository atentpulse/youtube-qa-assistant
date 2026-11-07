import React, { useState } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { useToast } from '../../../context/ToastContext';
import { updateProfile } from '../../../api/auth';
import { Check, ShieldCheck, Mail, Calendar, UserCheck, LogOut } from 'lucide-react';
import common from './CategoryCommon.module.css';

export default function AccountCategory({ onTriggerLogout }) {
  const { user } = useAuth();
  const toast = useToast();
  const [username, setUsername] = useState(user?.username || '');
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const initial = (user?.username || user?.email || '?').charAt(0).toUpperCase();

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    const trimmed = username.trim();
    if (!trimmed) {
      toast.error('Display name cannot be blank.');
      return;
    }
    if (trimmed === user?.username) {
      return;
    }

    setIsSaving(true);
    setSavedSuccess(false);
    try {
      const updated = await updateProfile({ username: trimmed });
      // Update local state and auth context if supported
      if (user) {
        user.username = updated.username;
      }
      toast.success('Display name updated successfully.');
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (err) {
      toast.error(err?.message || 'Failed to update display name.');
    } finally {
      setIsSaving(false);
    }
  };

  const formattedDate = user?.created_at
    ? new Date(user.created_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : 'Not available';

  const isGoogle = user?.auth_provider === 'google';

  return (
    <div className={common.container}>
      <div className={common.header}>
        <h2 className={common.title}>My Account</h2>
        <p className={common.description}>
          Manage your personal profile details, authentication provider, and account status.
        </p>
      </div>

      {/* Profile Overview */}
      <div className={common.section}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: '#333333',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '24px',
              fontWeight: '600',
              flexShrink: 0,
            }}
          >
            {initial}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text-primary)' }}>
                {user?.username || 'User'}
              </span>
              {user?.email_verified ? (
                <span className={`${common.badge} ${common.badgeSuccess}`}>
                  <Check size={12} /> Verified
                </span>
              ) : (
                <span className={`${common.badge} ${common.badgeWarning}`}>
                  Pending Verification
                </span>
              )}
            </div>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              {user?.email || 'No email associated'}
            </span>
            <span style={{ fontSize: '11.5px', color: '#777777' }}>
              Avatar upload is not enabled in this environment (Google profile picture used for OAuth).
            </span>
          </div>
        </div>
      </div>

      {/* Profile Information Form */}
      <form onSubmit={handleSaveProfile} className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Profile Details</h3>
          <p className={common.sectionSubtitle}>
            Update how your name appears throughout YtGenius workspaces and citations.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <label htmlFor="displayNameInput" className={common.rowLabel}>
              Display Name
            </label>
            <span className={common.rowDescription}>
              Visible across conversations, video comments, and activity logs.
            </span>
          </div>
          <input
            id="displayNameInput"
            type="text"
            className={common.input}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            minLength={2}
            maxLength={100}
            required
            data-testid="settings-username-input"
          />
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Email Address</span>
            <span className={common.rowDescription}>
              Primary email used for account authentication and security communications.
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13.5px', color: 'var(--text-secondary)' }}>
              {user?.email}
            </span>
            <span className={`${common.badge} ${common.badgeNeutral}`}>
              <Mail size={12} /> Primary
            </span>
          </div>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Authentication Provider</span>
            <span className={common.rowDescription}>
              The identity provider used to authenticate your account.
            </span>
          </div>
          <span className={`${common.badge} ${common.badgeBlue}`}>
            <ShieldCheck size={12} /> {isGoogle ? 'Google OAuth 2.0' : 'Email & Password'}
          </span>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Account Created</span>
            <span className={common.rowDescription}>
              The date your YtGenius account was originally registered.
            </span>
          </div>
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Calendar size={13} /> {formattedDate}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingTop: '10px' }}>
          <button
            type="submit"
            className={common.btnPrimary}
            disabled={isSaving || username.trim() === user?.username}
            data-testid="settings-save-profile-btn"
          >
            <UserCheck size={14} />
            {isSaving ? 'Saving Changes…' : 'Save Changes'}
          </button>
          {savedSuccess && (
            <span className={common.saveIndicator}>
              <Check size={14} /> Changes saved
            </span>
          )}
        </div>
      </form>

      {/* Account Session Actions */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Account Session</h3>
          <p className={common.sectionSubtitle}>
            End your active session on this device.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Log Out</span>
            <span className={common.rowDescription}>
              Safely clears authentication tokens and returns you to the login screen.
            </span>
          </div>
          <button
            type="button"
            className={common.btnSecondary}
            onClick={onTriggerLogout}
            data-testid="settings-signout-btn"
          >
            <LogOut size={14} /> Log Out
          </button>
        </div>
      </div>
    </div>
  );
}
