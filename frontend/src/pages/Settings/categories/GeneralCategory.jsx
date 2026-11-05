import React from 'react';
import { usePreferences } from '../../../context/PreferencesContext';
import { Moon, Globe, Check } from 'lucide-react';
import common from './CategoryCommon.module.css';

export default function GeneralCategory() {
  const { preferences, updatePreference, saveStatus } = usePreferences();

  return (
    <div className={common.container}>
      <div className={common.header}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 className={common.title}>General Preferences</h2>
            <p className={common.description}>
              Configure your default workspace layout, citation timestamp formatting, and video behaviors.
            </p>
          </div>
          {saveStatus === 'saved' && (
            <span className={common.saveIndicator}>
              <Check size={14} /> Saved
            </span>
          )}
        </div>
      </div>

      {/* Interface & Theme (Strictly Dark Theme) */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Appearance &amp; Theme</h3>
          <p className={common.sectionSubtitle}>
            YtGenius is engineered exclusively with a high-contrast dark visual system.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Application Theme</span>
            <span className={common.rowDescription}>
              High-contrast charcoal canvas (#0F0F0F) inspired by YouTube and ChatGPT dark modes.
            </span>
          </div>
          <span className={`${common.badge} ${common.badgeNeutral}`}>
            <Moon size={12} /> Dark Theme (Strict)
          </span>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Language</span>
            <span className={common.rowDescription}>
              Primary language for interface navigation, error messages, and system prompts.
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              English (United States)
            </span>
            <span className={`${common.badge} ${common.badgeNeutral}`}>
              <Globe size={11} /> Default
            </span>
          </div>
        </div>
      </div>

      {/* Timestamp & Video Playback */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Video &amp; Citations</h3>
          <p className={common.sectionSubtitle}>
            Control how video time markers and interactive citations are displayed and navigated.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <label htmlFor="timestampFormatSelect" className={common.rowLabel}>
              Timestamp Format
            </label>
            <span className={common.rowDescription}>
              Display timestamps as standard minutes/seconds (02:45) or full hours (00:02:45).
            </span>
          </div>
          <select
            id="timestampFormatSelect"
            className={common.select}
            value={preferences.timestampFormat}
            onChange={(e) => updatePreference('timestampFormat', e.target.value)}
            data-testid="settings-timestamp-format-select"
          >
            <option value="MM:SS">MM:SS (e.g. 02:45)</option>
            <option value="HH:MM:SS">HH:MM:SS (e.g. 00:02:45)</option>
          </select>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Auto-play on Citation Click</span>
            <span className={common.rowDescription}>
              Immediately resume YouTube video playback when clicking a timestamp citation chip.
            </span>
          </div>
          <label className={common.switch} aria-label="Auto-play on citation click">
            <input
              type="checkbox"
              checked={preferences.autoPlayOnCitation}
              onChange={(e) => updatePreference('autoPlayOnCitation', e.target.checked)}
              data-testid="settings-autoplay-citation-switch"
            />
            <span className={common.slider} />
          </label>
        </div>
      </div>

      {/* Workspace & Navigation */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Workspace Layout</h3>
          <p className={common.sectionSubtitle}>
            Configure sidebar default density and startup landing behavior.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Default Sidebar Collapsed</span>
            <span className={common.rowDescription}>
              Keep the sidebar minimized to an icon rail on startup to maximize stage research area.
            </span>
          </div>
          <label className={common.switch} aria-label="Default sidebar collapsed">
            <input
              type="checkbox"
              checked={preferences.sidebarDefaultCollapsed}
              onChange={(e) => updatePreference('sidebarDefaultCollapsed', e.target.checked)}
              data-testid="settings-sidebar-collapsed-switch"
            />
            <span className={common.slider} />
          </label>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <label htmlFor="workspaceLandingSelect" className={common.rowLabel}>
              Startup Landing Mode
            </label>
            <span className={common.rowDescription}>
              Choose what opens automatically when navigating to the workspace.
            </span>
          </div>
          <select
            id="workspaceLandingSelect"
            className={common.select}
            value={preferences.defaultWorkspaceLanding}
            onChange={(e) => updatePreference('defaultWorkspaceLanding', e.target.value)}
            data-testid="settings-landing-mode-select"
          >
            <option value="resume">Resume last active video</option>
            <option value="empty">Start with empty research stage</option>
          </select>
        </div>
      </div>
    </div>
  );
}
