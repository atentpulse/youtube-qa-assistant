import React, { createContext, useCallback, useContext, useEffect } from 'react';

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  // YtGenius is strictly Dark Theme Only.
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
    try {
      window.localStorage.setItem('ytgenius_theme', 'dark');
      if (window.localStorage.getItem('vidmind_theme')) {
        window.localStorage.removeItem('vidmind_theme');
      }
    } catch {
      // Ignore storage write failures
    }
  }, []);

  // No-op for compatibility if called anywhere
  const toggleTheme = useCallback(() => {
    // Permanently locked to dark theme
  }, []);

  return (
    <ThemeContext.Provider value={{ theme: 'dark', toggleTheme, isDark: true }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider');
  return ctx;
}
