import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  User,
  SlidersHorizontal,
  Sparkles,
  Bell,
  Database,
  ShieldCheck,
  Info,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import Modal from '../../components/common/Modal';

import AccountCategory from './categories/AccountCategory';
import GeneralCategory from './categories/GeneralCategory';
import PersonalizationCategory from './categories/PersonalizationCategory';
import NotificationsCategory from './categories/NotificationsCategory';
import DataPrivacyCategory from './categories/DataPrivacyCategory';
import SecurityCategory from './categories/SecurityCategory';
import AboutCategory from './categories/AboutCategory';

import styles from './SettingsPage.module.css';

const CATEGORIES = [
  { id: 'account', label: 'My Account', icon: User },
  { id: 'general', label: 'General', icon: SlidersHorizontal },
  { id: 'personalization', label: 'Personalization', icon: Sparkles },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'data', label: 'Data & Privacy', icon: Database },
  { id: 'security', label: 'Security', icon: ShieldCheck },
  { id: 'about', label: 'About', icon: Info },
];

export default function SettingsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { logout } = useAuth();

  const activeCategory = searchParams.get('category') || 'account';
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);

  const handleSelectCategory = (id) => {
    setSearchParams({ category: id }, { replace: true });
  };

  const handleConfirmLogout = () => {
    setIsLogoutModalOpen(false);
    logout();
    navigate('/', { replace: true });
  };

  const renderActiveCategory = () => {
    switch (activeCategory) {
      case 'account':
        return <AccountCategory onTriggerLogout={() => setIsLogoutModalOpen(true)} />;
      case 'general':
        return <GeneralCategory />;
      case 'personalization':
        return <PersonalizationCategory />;
      case 'notifications':
        return <NotificationsCategory />;
      case 'data':
        return <DataPrivacyCategory />;
      case 'security':
        return (
          <SecurityCategory
            onTriggerLogout={() => setIsLogoutModalOpen(true)}
            onNavigateCategory={handleSelectCategory}
          />
        );
      case 'about':
        return <AboutCategory />;
      default:
        return <AccountCategory onTriggerLogout={() => setIsLogoutModalOpen(true)} />;
    }
  };

  return (
    <div className={styles.settingsShell}>
      {/* Desktop Navigation Column */}
      <aside className={styles.navColumn} aria-label="Settings navigation">
        <button
          type="button"
          className={styles.backButton}
          onClick={() => navigate('/app')}
          aria-label="Back to workspace"
          data-testid="settings-back-button"
        >
          <ArrowLeft size={16} />
          <span>Back to Workspace</span>
        </button>

        <div className={styles.navHeader}>
          <h1 className={styles.navTitle}>Settings</h1>
        </div>

        <nav>
          <ul className={styles.navList}>
            {CATEGORIES.map((cat) => {
              const Icon = cat.icon;
              const isActive = activeCategory === cat.id;
              return (
                <li key={cat.id}>
                  <button
                    type="button"
                    className={`${styles.navItem} ${isActive ? styles.navItemActive : ''}`}
                    onClick={() => handleSelectCategory(cat.id)}
                    aria-current={isActive ? 'page' : undefined}
                    data-testid={`settings-nav-${cat.id}`}
                  >
                    <Icon size={16} className={styles.navIcon} />
                    <span>{cat.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>

      {/* Mobile Top Navigation */}
      <div className={styles.mobileNavHeader}>
        <div className={styles.mobileTopRow}>
          <button
            type="button"
            className={styles.backButton}
            onClick={() => navigate('/app')}
            aria-label="Back to workspace"
            data-testid="settings-back-button-mobile"
          >
            <ArrowLeft size={15} />
            <span>Workspace</span>
          </button>
          <span style={{ fontSize: '15px', fontWeight: '700' }}>Settings</span>
        </div>

        <div className={styles.mobileScrollTrack} role="tablist">
          {CATEGORIES.map((cat) => {
            const isActive = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                className={`${styles.mobileNavChip} ${isActive ? styles.mobileNavChipActive : ''}`}
                onClick={() => handleSelectCategory(cat.id)}
                data-testid={`settings-mobile-chip-${cat.id}`}
              >
                <span>{cat.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Settings Content Area */}
      <main className={styles.contentColumn} tabIndex={-1}>
        {renderActiveCategory()}
      </main>

      {/* Logout Confirmation Dialog */}
      <Modal
        isOpen={isLogoutModalOpen}
        onClose={() => setIsLogoutModalOpen(false)}
        title="Log out of YtGenius?"
        confirmLabel="Log Out"
        cancelLabel="Cancel"
        isDestructive
        onConfirm={handleConfirmLogout}
      >
        <p>Are you sure you want to end your active research session?</p>
      </Modal>
    </div>
  );
}
