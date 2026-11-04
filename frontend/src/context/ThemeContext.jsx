import React, { createContext, useCallback, useContext, useEffect } from 'react';

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  // VidMind is strictly Dark Theme Only.
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
    try {
      window.localStorage.setItem('vidmind_theme', 'dark');
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
