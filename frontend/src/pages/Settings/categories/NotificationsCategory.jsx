import React from 'react';
import { usePreferences } from '../../../context/PreferencesContext';
import { Info, Check } from 'lucide-react';
import common from './CategoryCommon.module.css';

export default function NotificationsCategory() {
  const { preferences, updatePreference, saveStatus } = usePreferences();

  return (
    <div className={common.container}>
      <div className={common.header}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 className={common.title}>Notifications</h2>
            <p className={common.description}>
              Manage in-app toasts and review channel delivery configuration.
            </p>
          </div>
          {saveStatus === 'saved' && (
            <span className={common.saveIndicator}>
              <Check size={14} /> Saved
            </span>
          )}
        </div>
      </div>

      {/* Deployment Channel Status Box */}
      <div className={common.noticeBox}>
        <Info size={18} className={common.noticeIcon} />
        <div>
          <strong style={{ color: '#ffffff', display: 'block', marginBottom: '2px' }}>
            Notification Delivery Status
          </strong>
          <span>
            In-app toasts and essential account security emails (verification and password recovery) are active. Background email workers for video processing events and browser push notifications are not configured in this self-hosted environment.
          </span>
        </div>
      </div>

      {/* In-App Notifications (Real & Active) */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>In-App Notifications</h3>
          <p className={common.sectionSubtitle}>
            Feedback and alerts displayed within the YtGenius workspace while you work.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>In-App Toast Alerts</span>
            <span className={common.rowDescription}>
              Display toast popups for video processing status, chat errors, and preference updates.
            </span>
          </div>
          <label className={common.switch} aria-label="In-app toast alerts">
            <input
              type="checkbox"
              checked={preferences.inAppToasts}
              onChange={(e) => updatePreference('inAppToasts', e.target.checked)}
              data-testid="settings-inapp-toasts-switch"
            />
            <span className={common.slider} />
          </label>
        </div>
      </div>

      {/* External Notification Channels (Transparently Disclosed) */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Email &amp; Push Channels</h3>
          <p className={common.sectionSubtitle}>
            Background event notifications requiring external delivery workers.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Video Processing Complete</span>
            <span className={common.rowDescription}>
              Receive an email when long YouTube transcripts finish ingestion and chunking.
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className={`${common.badge} ${common.badgeNeutral}`}>
              Not configured in deployment
            </span>
            <label className={`${common.switch} ${common.switchDisabled}`} title="Background email worker not configured">
              <input type="checkbox" disabled checked={false} />
              <span className={common.slider} />
            </label>
          </div>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Video Processing Failure Alerts</span>
            <span className={common.rowDescription}>
              Receive an alert if YouTube captions cannot be retrieved or rate-limits are hit.
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className={`${common.badge} ${common.badgeNeutral}`}>
              Not configured in deployment
            </span>
            <label className={`${common.switch} ${common.switchDisabled}`} title="Background email worker not configured">
              <input type="checkbox" disabled checked={false} />
              <span className={common.slider} />
            </label>
          </div>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Security &amp; Account Alerts</span>
            <span className={common.rowDescription}>
              Email verification and password reset links dispatched via configured SMTP.
            </span>
          </div>
          <span className={`${common.badge} ${common.badgeSuccess}`}>
            <Check size={11} /> Active (Transactional)
          </span>
        </div>
      </div>
    </div>
  );
}
