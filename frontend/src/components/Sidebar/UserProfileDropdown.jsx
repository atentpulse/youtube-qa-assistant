import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Settings, HelpCircle, LogOut, ChevronUp } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import styles from './UserProfileDropdown.module.css';

export default function UserProfileDropdown({ isCollapsed = false, onTriggerLogout }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const initial = (user?.username || user?.email || '?').charAt(0).toUpperCase();

  // Close on outside click or Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleOutsideClick = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    document.addEventListener('touchstart', handleOutsideClick);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('touchstart', handleOutsideClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleNavigate = (category) => {
    setIsOpen(false);
    navigate(`/settings?category=${category}`);
  };

  const handleSignOut = () => {
    setIsOpen(false);
    if (onTriggerLogout) {
      onTriggerLogout();
    }
  };

  return (
    <div className={styles.wrapper} ref={dropdownRef}>
      {/* Trigger Button */}
      {isCollapsed ? (
        <button
          type="button"
          className={`${styles.triggerBtnCollapsed} ${isOpen ? styles.triggerBtnActive : ''}`}
          onClick={() => setIsOpen((prev) => !prev)}
          aria-label="User profile and settings"
          aria-expanded={isOpen}
          title={user?.username || user?.email || 'Account menu'}
          data-testid="profile-menu-button"
        >
          <div className={styles.avatar}>{initial}</div>
        </button>
      ) : (
        <button
          type="button"
          className={`${styles.triggerBtn} ${isOpen ? styles.triggerBtnActive : ''}`}
          onClick={() => setIsOpen((prev) => !prev)}
          aria-label="User profile and settings"
          aria-expanded={isOpen}
          data-testid="profile-menu-button"
        >
          <div className={styles.avatar}>{initial}</div>
          <div className={styles.userMeta}>
            <span className={styles.userName} title={user?.username || 'User'}>
              {user?.username || 'User'}
            </span>
            <span className={styles.userEmail} title={user?.email || ''}>
              {user?.email || ''}
            </span>
          </div>
          <ChevronUp
            size={14}
            className={`${styles.chevronIcon} ${isOpen ? styles.chevronOpen : ''}`}
          />
        </button>
      )}

      {/* Floating Dropdown Menu */}
      {isOpen && (
        <div
          className={`${styles.dropdown} ${isCollapsed ? styles.dropdownCollapsed : ''}`}
          role="menu"
          aria-orientation="vertical"
          data-testid="profile-dropdown-menu"
        >
          <div className={styles.dropdownHeader}>
            <div className={styles.dropdownHeaderAvatar}>{initial}</div>
            <div className={styles.userMeta}>
              <span className={styles.userName}>{user?.username || 'User'}</span>
              <span className={styles.userEmail}>{user?.email || ''}</span>
            </div>
          </div>

          <button
            type="button"
            role="menuitem"
            className={styles.menuItem}
            onClick={() => handleNavigate('account')}
            data-testid="profile-menu-my-account"
          >
            <User size={15} className={styles.menuIcon} />
            <span>My Account</span>
          </button>

          <button
            type="button"
            role="menuitem"
            className={styles.menuItem}
            onClick={() => handleNavigate('general')}
            data-testid="profile-menu-settings"
          >
            <Settings size={15} className={styles.menuIcon} />
            <span>Settings</span>
          </button>

          <button
            type="button"
            role="menuitem"
            className={styles.menuItem}
            onClick={() => handleNavigate('about')}
            data-testid="profile-menu-help"
          >
            <HelpCircle size={15} className={styles.menuIcon} />
            <span>Help &amp; Support</span>
          </button>

          <div className={styles.menuDivider} role="separator" />

          <button
            type="button"
            role="menuitem"
            className={`${styles.menuItem} ${styles.menuItemDanger}`}
            onClick={handleSignOut}
            data-testid="profile-menu-sign-out"
          >
            <LogOut size={15} className={styles.menuIcon} />
            <span>Log Out</span>
          </button>
        </div>
      )}
    </div>
  );
}
