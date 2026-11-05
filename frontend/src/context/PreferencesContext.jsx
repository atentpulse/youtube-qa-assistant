import React, { createContext, useCallback, useContext, useState } from 'react';

const PREFERENCES_STORAGE_KEY = 'ytgenius_user_preferences';

export const DEFAULT_PREFERENCES = {
  // General
  timestampFormat: 'MM:SS', // 'MM:SS' | 'HH:MM:SS'
  sidebarDefaultCollapsed: false,
  defaultWorkspaceLanding: 'resume', // 'resume' | 'empty'
  autoPlayOnCitation: true,
  inAppToasts: true,

  // Personalization (AI Research)
  answerLength: 'balanced', // 'concise' | 'balanced' | 'detailed'
  responseStyle: 'explanatory', // 'simple' | 'technical' | 'explanatory'
  preferStructured: true,
  includeExamples: false,
  showCitations: true,
};

const PreferencesContext = createContext(null);

export function PreferencesProvider({ children }) {
  const [preferences, setPreferencesState] = useState(() => {
    if (typeof window === 'undefined') return DEFAULT_PREFERENCES;
    try {
      const stored = window.localStorage.getItem(PREFERENCES_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return { ...DEFAULT_PREFERENCES, ...parsed };
      }
    } catch {
      // Fallback on JSON parse error
    }
    return DEFAULT_PREFERENCES;
  });

  const [saveStatus, setSaveStatus] = useState('idle'); // 'idle' | 'saving' | 'saved'

  // Persist to localStorage whenever preferences change
  const saveToStorage = useCallback((newPrefs) => {
    try {
      window.localStorage.setItem(PREFERENCES_STORAGE_KEY, JSON.stringify(newPrefs));
      // Keep legacy sidebar collapse preference key in sync
      if (newPrefs.sidebarDefaultCollapsed !== undefined) {
        window.localStorage.setItem('ytgenius_sidebar_collapsed', String(newPrefs.sidebarDefaultCollapsed));
      }
    } catch {
      // Ignore quota errors in private browsing
    }
  }, []);

  const updatePreference = useCallback((key, value) => {
    setSaveStatus('saving');
    setPreferencesState((prev) => {
      const next = { ...prev, [key]: value };
      saveToStorage(next);
      return next;
    });
    setTimeout(() => {
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 1800);
    }, 150);
  }, [saveToStorage]);

  const updatePreferences = useCallback((partial) => {
    setSaveStatus('saving');
    setPreferencesState((prev) => {
      const next = { ...prev, ...partial };
      saveToStorage(next);
      return next;
    });
    setTimeout(() => {
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 1800);
    }, 200);
  }, [saveToStorage]);

  const resetPreferences = useCallback(() => {
    setSaveStatus('saving');
    setPreferencesState(DEFAULT_PREFERENCES);
    saveToStorage(DEFAULT_PREFERENCES);
    setTimeout(() => {
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 1800);
    }, 150);
  }, [saveToStorage]);

  // Format timestamp in seconds according to current user preference
  const formatSeconds = useCallback((totalSeconds) => {
    if (totalSeconds === null || totalSeconds === undefined || isNaN(totalSeconds)) {
      return '00:00';
    }
    const sec = Math.max(0, Math.floor(Number(totalSeconds)));
    const hours = Math.floor(sec / 3600);
    const minutes = Math.floor((sec % 3600) / 60);
    const seconds = sec % 60;

    const pad = (n) => String(n).padStart(2, '0');

    if (preferences.timestampFormat === 'HH:MM:SS' || hours > 0) {
      return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    }
    return `${pad(minutes)}:${pad(seconds)}`;
  }, [preferences.timestampFormat]);

  const value = {
    preferences,
    saveStatus,
    updatePreference,
    updatePreferences,
    resetPreferences,
    formatSeconds,
  };

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences() {
  const ctx = useContext(PreferencesContext);
  if (!ctx) {
    throw new Error('usePreferences must be used within a PreferencesProvider');
  }
  return ctx;
}
